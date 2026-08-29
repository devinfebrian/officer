import json
import sqlite3
import threading
import time

import httpx
import pytest
import uvicorn

from purchase_office.audit import AuditTrail
from purchase_office.dashboard.app import create_app


@pytest.fixture
def office(tmp_path):
    """A real uvicorn server tailing a scratch audit DB. Yields (base_url, audit_path)."""
    audit_path = tmp_path / "audit.db"
    app = create_app(audit_path=audit_path, stream_poll_seconds=0.05)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}", audit_path
    server.should_exit = True
    thread.join(timeout=5)


def _seed(audit_path, triples):
    trail = AuditTrail(audit_path)
    for role, action in triples:
        trail.append(request_id="req-1", role=role, action=action, status="ok")
    trail.close()


def _data_events(lines):
    events = []
    for line in lines:
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:") :].strip()))
    return events


def test_stream_backfills_then_goes_live(office):
    base_url, audit_path = office
    _seed(audit_path, [("watcher", "enter"), ("guardrail", "screen")])
    trail = AuditTrail(audit_path)

    got_legal = threading.Event()

    def poison():
        time.sleep(0.3)
        trail.append(request_id="req-1", role="legal", action="enter", status="ok")
        trail.close()

    threading.Thread(target=poison, daemon=True).start()

    seen = []
    with httpx.stream("GET", f"{base_url}/api/stream", timeout=10) as response:
        for line in response.iter_lines():
            if line.startswith("data:"):
                event = json.loads(line[len("data:") :].strip())
                seen.append(event)
                if event["role"] == "legal":
                    got_legal.set()
                    break

    assert got_legal.is_set()
    assert [e["seq"] for e in seen] == [1, 2, 3]


def test_since_param_backfills_from_cursor(office):
    base_url, audit_path = office
    _seed(audit_path, [("watcher", "enter"), ("procurement", "enter"), ("legal", "enter")])

    frames = []
    with httpx.stream("GET", f"{base_url}/api/stream", params={"after": 1}, timeout=10) as response:
        for line in response.iter_lines():
            if line.startswith("data:"):
                frames.append(line)
                if len(frames) == 2:
                    break

    assert [e["seq"] for e in _data_events(frames)] == [2, 3]


def test_last_event_id_header_overrides_since(office):
    base_url, audit_path = office
    _seed(audit_path, [("watcher", "enter"), ("procurement", "enter"), ("legal", "enter")])

    frames = []
    with httpx.stream(
        "GET",
        f"{base_url}/api/stream",
        params={"after": 0},
        headers={"Last-Event-ID": "1"},
        timeout=10,
    ) as response:
        for line in response.iter_lines():
            if line.startswith("data:"):
                frames.append(line)
                if len(frames) == 2:
                    break

    assert [e["seq"] for e in _data_events(frames)] == [2, 3]


def test_frames_carry_event_type_and_seq_id(office):
    base_url, audit_path = office
    _seed(audit_path, [("watcher", "enter")])

    lines = []
    with httpx.stream("GET", f"{base_url}/api/stream", timeout=10) as response:
        for line in response.iter_lines():
            lines.append(line)
            if line.startswith("data:"):
                break

    assert "event: audit" in lines
    assert "id: 1" in lines
