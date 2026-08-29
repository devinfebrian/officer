"""Runner: starts the office in a background thread; crashes become audit events."""

import os
import sqlite3
import threading
import uuid
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from ..audit import AuditTrail, ensure_schema
from ..config import load_registry
from ..llm import GeminiLLMClient
from ..orchestrator import build_graph

DEFAULT_REQUEST = {"item": "widget", "quantity": 5, "reason": "stock low"}

DEFAULT_STORES = {
    "inventory": {"widget": {"stock": 3, "reorder_threshold": 5}},
    "vendors": [
        {
            "name": "Acme Supply",
            "item": "widget",
            "quote": 120.0,
            "contract": "Standard terms. Payment net 30.",
        }
    ],
    "budget": {"limit": 200.0},
    "sanctions": [],
}


def load_env_file(path: str | Path | None = None) -> None:
    """Load KEY=VALUE pairs from a .env file into the environment.

    The real environment always wins: a variable already set in the shell is
    never overridden. No value is ever logged.
    """
    path = Path(path or ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def default_llm_factory(name: str):
    return GeminiLLMClient(os.environ.get(f"AGENT_{name.upper()}_KEY"))


def default_stores_factory() -> dict:
    return {key: value for key, value in DEFAULT_STORES.items()}


class Runner:
    def __init__(
        self,
        registry_path,
        audit_path,
        checkpoint_path,
        llm_factory=None,
        stores_factory=None,
    ):
        self.registry_path = Path(registry_path or "config/registry.yaml")
        self.audit_path = Path(audit_path or "data/audit.db")
        self.checkpoint_path = Path(checkpoint_path or "data/checkpoints.db")
        self.llm_factory = llm_factory or default_llm_factory
        self.stores_factory = stores_factory or default_stores_factory
        self._known = set()
        self._lock = threading.Lock()
        self._check_conn = sqlite3.connect(self.audit_path, check_same_thread=False)
        ensure_schema(self._check_conn)

    def start(self, request_id: str | None, request: dict | None) -> tuple[str, bool]:
        request_id = request_id or f"case-{uuid.uuid4().hex[:8]}"
        request = request or DEFAULT_REQUEST
        with self._lock:
            if request_id in self._known or self._already_known(request_id):
                return request_id, False
            self._known.add(request_id)
        threading.Thread(
            target=self._run, args=(request_id, request), daemon=True
        ).start()
        return request_id, True

    def _already_known(self, request_id: str) -> bool:
        row = self._check_conn.execute(
            "SELECT 1 FROM events WHERE request_id = ? LIMIT 1", (request_id,)
        ).fetchone()
        return row is not None

    def _run(self, request_id: str, request: dict) -> None:
        audit = AuditTrail(self.audit_path)
        try:
            registry = load_registry(self.registry_path)
            checkpoint_conn = sqlite3.connect(
                self.checkpoint_path, check_same_thread=False
            )
            checkpointer = SqliteSaver(checkpoint_conn)
            graph = build_graph(
                registry,
                llm_factory=self.llm_factory,
                stores=self.stores_factory(),
                audit=audit,
                checkpointer=checkpointer,
            )
            graph.invoke(
                {"request_id": request_id, "request": request},
                config={"configurable": {"thread_id": request_id}},
            )
        except Exception as exc:
            audit.append(
                request_id=request_id,
                role="office",
                action="error",
                status="FAILED",
                detail=str(exc)[:500],
            )
        finally:
            audit.close()
