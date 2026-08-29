"""Audit Trail: the immutable, append-only record of who touched the case.

Every event is a row in one SQLite table. There is no update or delete —
the trail only grows, in the order events happened.
"""

import sqlite3
from datetime import datetime, timezone

from pydantic import BaseModel


class AuditEvent(BaseModel):
    seq: int
    ts: str
    request_id: str
    role: str
    action: str
    status: str
    detail: str


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    request_id TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT NOT NULL
)
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(SCHEMA)
    conn.commit()


class AuditTrail:
    def __init__(self, path):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        ensure_schema(self._conn)

    def append(self, request_id: str, role: str, action: str, status: str, detail: str = "") -> None:
        ts = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO events (ts, request_id, role, action, status, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, request_id, role, action, status, detail),
        )
        self._conn.commit()

    def read(self, request_id: str | None = None) -> list[AuditEvent]:
        if request_id is None:
            rows = self._conn.execute(
                "SELECT seq, ts, request_id, role, action, status, detail FROM events ORDER BY seq"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT seq, ts, request_id, role, action, status, detail FROM events WHERE request_id = ? ORDER BY seq",
                (request_id,),
            ).fetchall()
        return [AuditEvent(**row) for row in rows]

    def close(self) -> None:
        self._conn.close()
