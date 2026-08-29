from purchase_office.audit import AuditTrail


def test_append_then_read_returns_events_in_order(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")
    trail.append(
        request_id="req-1", role="procurement", action="verdict", status="approve", detail="ok"
    )
    trail.append(request_id="req-1", role="guardrail", action="screen", status="pass", detail="pii")

    events = trail.read()

    assert [(e.role, e.action, e.status) for e in events] == [
        ("procurement", "verdict", "approve"),
        ("guardrail", "screen", "pass"),
    ]


def test_every_event_is_timestamped_and_scoped_to_request(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")
    trail.append(request_id="req-1", role="watcher", action="enter", status="ok", detail="")

    (event,) = trail.read()
    assert event.ts
    assert event.request_id == "req-1"
    assert event.detail == ""


def test_read_filters_by_request_id(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db")
    trail.append(request_id="req-1", role="procurement", action="verdict", status="approve", detail="")
    trail.append(request_id="req-2", role="procurement", action="verdict", status="approve", detail="")

    only = trail.read(request_id="req-2")

    assert len(only) == 1
    assert only[0].request_id == "req-2"


def test_events_survive_reopen(tmp_path):
    path = tmp_path / "audit.db"
    trail = AuditTrail(path)
    trail.append(request_id="req-1", role="watcher", action="enter", status="ok", detail="")
    trail.close()

    reopened = AuditTrail(path)

    assert len(reopened.read()) == 1
    assert reopened.read()[0].role == "watcher"
