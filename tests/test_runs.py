import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from purchase_office.dashboard.app import create_app
from purchase_office.dashboard.runner import load_env_file
from purchase_office.llm import FakeLLMClient

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


def _app(tmp_path, llm_factory=None):
    return create_app(
        registry_path=REGISTRY_PATH,
        audit_path=tmp_path / "audit.db",
        checkpoint_path=tmp_path / "checkpoints.db",
        llm_factory=llm_factory
        or (lambda name: FakeLLMClient({"decision": "approve", "note": "ok"})),
        stores_factory=lambda: dict(STORES),
    )


def _await_terminal(client, request_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get("/api/events", params={"request_id": request_id}).json()
        terminals = [
            e for e in body["events"] if e["action"] in ("status", "error")
        ]
        if terminals:
            return body
        time.sleep(0.05)
    raise AssertionError(f"case {request_id} never reached a terminal event")


def test_run_a_case_files_it_and_records_the_story(tmp_path):
    app = _app(tmp_path)

    with TestClient(app) as client:
        response = client.post("/api/runs", json={"request_id": "case-1"})

        assert response.status_code == 202
        assert response.json() == {"request_id": "case-1", "started": True}

        body = _await_terminal(client, "case-1")

    assert ("status", "FILED") in [(e["action"], e["status"]) for e in body["events"]]
    actions = [(e["role"], e["action"]) for e in body["events"]]
    assert actions[0] == ("watcher", "enter")


def test_repeat_run_with_same_id_is_idempotent(tmp_path):
    app = _app(tmp_path)

    with TestClient(app) as client:
        first = client.post("/api/runs", json={"request_id": "case-1"})
        repeat = client.post("/api/runs", json={"request_id": "case-1"})
        _await_terminal(client, "case-1")

        body = client.get("/api/events", params={"request_id": "case-1"}).json()

    assert first.status_code == 202
    assert repeat.status_code == 200
    assert repeat.json() == {"request_id": "case-1", "started": False}
    watcher_enters = [
        e for e in body["events"] if e["role"] == "watcher" and e["action"] == "enter"
    ]
    assert len(watcher_enters) == 1


def test_known_request_id_stays_started_after_a_restart(tmp_path):
    paths = {
        "registry_path": REGISTRY_PATH,
        "audit_path": tmp_path / "audit.db",
        "checkpoint_path": tmp_path / "checkpoints.db",
    }

    with TestClient(_app(tmp_path)) as client:
        client.post("/api/runs", json={"request_id": "case-1"})
        _await_terminal(client, "case-1")

    with TestClient(_app(tmp_path)) as client:
        response = client.post("/api/runs", json={"request_id": "case-1"})

    assert response.status_code == 200
    assert response.json() == {"request_id": "case-1", "started": False}


def test_run_without_body_generates_an_id_and_uses_canned_request(tmp_path):
    app = _app(tmp_path)

    with TestClient(app) as client:
        response = client.post("/api/runs", json={})

        assert response.status_code == 202
        request_id = response.json()["request_id"]
        assert request_id

        body = _await_terminal(client, request_id)

    assert ("status", "FILED") in [(e["action"], e["status"]) for e in body["events"]]


def test_empty_post_presses_play_with_no_body_at_all(tmp_path):
    app = _app(tmp_path)

    with TestClient(app) as client:
        response = client.post("/api/runs")

        assert response.status_code == 202
        request_id = response.json()["request_id"]
        assert request_id

        body = _await_terminal(client, request_id)

    assert ("status", "FILED") in [(e["action"], e["status"]) for e in body["events"]]


def test_env_file_secrets_reach_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text('GOOGLE_API_KEY = "test-key-123"\n', encoding="utf-8")

    load_env_file(env_path)

    assert os.environ["GOOGLE_API_KEY"] == "test-key-123"
    monkeypatch.delenv("GOOGLE_API_KEY")


def test_real_environment_wins_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "shell-key")
    env_path = tmp_path / ".env"
    env_path.write_text("GOOGLE_API_KEY=file-key\n", encoding="utf-8")

    load_env_file(env_path)

    assert os.environ["GOOGLE_API_KEY"] == "shell-key"


def test_missing_env_file_is_silently_ignored(tmp_path):
    load_env_file(tmp_path / "nope.env")


def test_crashed_run_records_an_error_event(tmp_path):
    def broken_factory(name):
        raise RuntimeError("no vendor for item 'jetpack'")

    app = _app(tmp_path, llm_factory=broken_factory)

    with TestClient(app) as client:
        client.post("/api/runs", json={"request_id": "case-1"})

        body = _await_terminal(client, "case-1")

    errors = [e for e in body["events"] if e["action"] == "error"]
    assert len(errors) == 1
    assert errors[0]["status"] == "FAILED"
    assert "jetpack" in errors[0]["detail"]
