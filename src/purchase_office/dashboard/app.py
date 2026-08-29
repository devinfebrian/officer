"""Dashboard API: the Audit Trail's tail over HTTP + SSE.

create_app is a uvicorn factory target:
    uvicorn purchase_office.dashboard.app:create_app --factory
"""

import json
import sqlite3
from pathlib import Path

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette import EventSourceResponse
from sse_starlette.sse import ServerSentEvent

from ..audit import AuditEvent, ensure_schema
from ..state import PurchaseRequest
from . import tail
from .runner import Runner, load_env_file


class EventsEnvelope(BaseModel):
    events: list[AuditEvent]
    cursor: int


class Health(BaseModel):
    ok: bool
    head_seq: int


class RunBody(BaseModel):
    request_id: str | None = None
    request: PurchaseRequest | None = None


def create_app(
    registry_path: str | Path | None = None,
    audit_path: str | Path | None = None,
    checkpoint_path: str | Path | None = None,
    llm_factory=None,
    stores_factory=None,
    stream_poll_seconds: float = 0.25,
) -> FastAPI:
    load_env_file()
    audit_path = Path(audit_path or "data/audit.db")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(audit_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    app = FastAPI(title="Purchase Office")
    runner = Runner(
        registry_path=registry_path,
        audit_path=audit_path,
        checkpoint_path=checkpoint_path,
        llm_factory=llm_factory,
        stores_factory=stores_factory,
    )

    @app.post("/api/runs")
    def start_run(body: RunBody | None = None):
        request_id, started = runner.start(
            body.request_id if body else None,
            body.request.model_dump() if body and body.request else None,
        )
        return JSONResponse(
            content={"request_id": request_id, "started": started},
            status_code=202 if started else 200,
        )

    @app.get("/api/events")
    def events(after: int = 0, request_id: str | None = None) -> EventsEnvelope:
        rows = tail.rows_after(conn, after, request_id)
        return EventsEnvelope(events=rows, cursor=tail.head_seq(conn))

    @app.get("/api/health")
    def health() -> Health:
        return Health(ok=True, head_seq=tail.head_seq(conn))

    @app.get("/api/stream")
    async def stream(request: Request, after: int = 0, request_id: str | None = None):
        last_event_id = request.headers.get("last-event-id")
        if last_event_id is not None:
            try:
                after = int(last_event_id)
            except ValueError:
                pass

        async def gen():
            yield ServerSentEvent(retry=1500)
            cursor = after
            while True:
                rows = await anyio.to_thread.run_sync(
                    lambda: tail.rows_after(conn, cursor, request_id)
                )
                if rows:
                    cursor = rows[-1]["seq"]
                for row in rows:
                    yield ServerSentEvent(
                        event="audit", id=str(row["seq"]), data=json.dumps(row)
                    )
                await anyio.sleep(stream_poll_seconds)

        return EventSourceResponse(gen(), ping=15)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
