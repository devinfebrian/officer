"""Tail the audit trail: cursor reads shared by the backlog API and the stream.

`after` is exclusive everywhere: a reader that has applied events up to seq N
asks for rows_after(conn, N) and never sees N again.
"""

import sqlite3

COLUMNS = "seq, ts, request_id, role, action, status, detail"


def head_seq(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
    return row[0]


def rows_after(
    conn: sqlite3.Connection, after: int, request_id: str | None = None
) -> list[dict]:
    if request_id is None:
        rows = conn.execute(
            f"SELECT {COLUMNS} FROM events WHERE seq > ? ORDER BY seq", (after,)
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {COLUMNS} FROM events WHERE seq > ? AND request_id = ? ORDER BY seq",
            (after, request_id),
        ).fetchall()
    return [dict(row) for row in rows]
