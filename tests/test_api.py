from fastapi.testclient import TestClient

from purchase_office.audit import AuditTrail
from purchase_office.dashboard.app import create_app


def _client(app) -> TestClient:
    return TestClient(app)


def _seed(audit_path, events):
    trail = AuditTrail(audit_path)
    for event in events:
        trail.append(**event)
    trail.close()


def test_empty_office_serves_an_empty_backlog(tmp_path):
    app = create_app(audit_path=tmp_path / "audit.db")

    with _client(app) as client:
        response = client.get("/api/events")

    assert response.status_code == 200
    assert response.json() == {"events": [], "cursor": 0}


def test_backlog_returns_seeded_events_ascending_with_cursor(tmp_path):
    audit_path = tmp_path / "audit.db"
    _seed(
        audit_path,
        [
            {"request_id": "req-1", "role": "watcher", "action": "enter", "status": "ok"},
            {"request_id": "req-1", "role": "guardrail", "action": "screen", "status": "pass"},
        ],
    )
    app = create_app(audit_path=audit_path)

    with _client(app) as client:
        body = client.get("/api/events").json()

    assert body["cursor"] == 2
    assert [(e["seq"], e["role"], e["action"]) for e in body["events"]] == [
        (1, "watcher", "enter"),
        (2, "guardrail", "screen"),
    ]


def test_after_is_exclusive(tmp_path):
    audit_path = tmp_path / "audit.db"
    _seed(
        audit_path,
        [
            {"request_id": "req-1", "role": "watcher", "action": "enter", "status": "ok"},
            {"request_id": "req-1", "role": "procurement", "action": "enter", "status": "ok"},
            {"request_id": "req-1", "role": "legal", "action": "enter", "status": "ok"},
        ],
    )
    app = create_app(audit_path=audit_path)

    with _client(app) as client:
        body = client.get("/api/events", params={"after": 1}).json()

    assert [e["seq"] for e in body["events"]] == [2, 3]
    assert body["cursor"] == 3


def test_request_id_filter(tmp_path):
    audit_path = tmp_path / "audit.db"
    _seed(
        audit_path,
        [
            {"request_id": "req-1", "role": "watcher", "action": "enter", "status": "ok"},
            {"request_id": "req-2", "role": "watcher", "action": "enter", "status": "ok"},
            {"request_id": "req-2", "role": "office", "action": "status", "status": "FILED"},
        ],
    )
    app = create_app(audit_path=audit_path)

    with _client(app) as client:
        body = client.get("/api/events", params={"request_id": "req-2"}).json()

    assert [e["request_id"] for e in body["events"]] == ["req-2", "req-2"]


def test_health_reports_head_seq(tmp_path):
    app = create_app(audit_path=tmp_path / "audit.db")

    with _client(app) as client:
        empty = client.get("/api/health").json()

    _seed(
        tmp_path / "audit.db",
        [
            {"request_id": "req-1", "role": "watcher", "action": "enter", "status": "ok"},
            {"request_id": "req-1", "role": "legal", "action": "enter", "status": "ok"},
        ],
    )

    with _client(app) as client:
        seeded = client.get("/api/health").json()

    assert empty == {"ok": True, "head_seq": 0}
    assert seeded == {"ok": True, "head_seq": 2}


def test_root_serves_the_records_room(tmp_path):
    app = create_app(audit_path=tmp_path / "audit.db")

    with _client(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Purchase Office" in response.text
    assert "text/html" in response.headers["content-type"]
