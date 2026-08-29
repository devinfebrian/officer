import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from purchase_office.config import load_registry
from purchase_office.llm import FakeLLMClient
from purchase_office.orchestrator import build_graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "config" / "registry.yaml"

STORES = {
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

INITIAL_STATE = {
    "request_id": "req-1",
    "request": {"item": "widget", "quantity": 5, "reason": "stock low"},
}


def _llm_factory(name):
    return FakeLLMClient({"decision": "approve", "note": "ok"})


def test_case_file_persists_across_a_fresh_checkpointer(tmp_path):
    reg = load_registry(REGISTRY_PATH)
    cp_path = tmp_path / "checkpoints.db"

    saver = SqliteSaver(sqlite3.connect(cp_path, check_same_thread=False))
    compiled = build_graph(reg, llm_factory=_llm_factory, stores=STORES, checkpointer=saver)
    result = compiled.invoke(
        INITIAL_STATE, config={"configurable": {"thread_id": "req-1"}}
    )
    saver.conn.close()

    fresh_saver = SqliteSaver(sqlite3.connect(cp_path, check_same_thread=False))
    fresh = build_graph(reg, llm_factory=_llm_factory, stores=STORES, checkpointer=fresh_saver)
    snapshot = fresh.get_state({"configurable": {"thread_id": "req-1"}})

    assert result["status"] == "FILED"
    assert snapshot.values["status"] == "FILED"
    assert list(snapshot.values["verdicts"].keys()) == [
        "procurement",
        "legal",
        "finance",
        "compliance",
    ]
    fresh_saver.conn.close()
