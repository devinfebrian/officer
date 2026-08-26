from pathlib import Path

import pytest
from pydantic import ValidationError

from purchase_office.config import ConfigError, load_registry
from purchase_office.orchestrator import build_graph
from purchase_office.state import CaseFile, PurchaseRequest, Verdict, WriteUp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "config" / "registry.yaml"


def _initial_state(**overrides):
    state = {
        "request_id": "req-1",
        "request": {"item": "widget", "quantity": 5, "reason": "stock low"},
    }
    state.update(overrides)
    return state


# --- Seam 1: Registry loading ---------------------------------------------

def test_load_registry_parses_roles_in_route_order():
    reg = load_registry(REGISTRY_PATH)
    assert [r.name for r in reg.roles] == [
        "watcher",
        "procurement",
        "legal",
        "finance",
        "compliance",
    ]


def test_load_registry_populates_identity_and_clearance():
    reg = load_registry(REGISTRY_PATH)
    by_name = {r.name: r for r in reg.roles}

    assert by_name["watcher"].identity == "AGENT_WATCHER_KEY"
    assert by_name["watcher"].next == ["procurement"]
    assert by_name["procurement"].clearance.tools == ["search_vendors", "select_vendor"]
    assert by_name["compliance"].next == ["done"]


def test_load_registry_parses_guardrail():
    reg = load_registry(REGISTRY_PATH)
    assert reg.guardrail.screens == ["injection", "pii", "role_policy"]
    assert reg.guardrail.policy["legal"] == [
        "vendor_details",
        "contract_terms",
        "internal_notes",
    ]


# --- Seam 1b: fail fast ----------------------------------------------------

def _write_registry(tmp_path, text):
    path = tmp_path / "registry.yaml"
    path.write_text(text)
    return path


def test_load_registry_rejects_unknown_next_role(tmp_path):
    path = _write_registry(
        tmp_path,
        """
roles:
  watcher:
    next: [ghost]
    identity: AGENT_WATCHER_KEY
    clearance:
      tools: [check_stock]
      read: [inventory]
guardrail:
  screens: [injection, pii, role_policy]
  policy: {}
""",
    )
    with pytest.raises(ConfigError):
        load_registry(path)


def test_load_registry_rejects_unknown_tool(tmp_path):
    path = _write_registry(
        tmp_path,
        """
roles:
  watcher:
    next: [done]
    identity: AGENT_WATCHER_KEY
    clearance:
      tools: [read_minds]
      read: [inventory]
guardrail:
  screens: [injection, pii, role_policy]
  policy: {}
""",
    )
    with pytest.raises(ConfigError):
        load_registry(path)


# --- Seam 2: state typing --------------------------------------------------

def test_purchase_request_fields():
    pr = PurchaseRequest(item="widget", quantity=5, reason="stock low")
    assert pr.item == "widget"
    assert pr.quantity == 5
    assert pr.reason == "stock low"


def test_verdict_accepts_only_approve_or_reject():
    Verdict(role="legal", decision="approve", note="ok")
    Verdict(role="legal", decision="reject", note="no")
    with pytest.raises(ValidationError):
        Verdict(role="legal", decision="maybe", note="?")


def test_casefile_defaults_to_raised_and_empty():
    cf = CaseFile(
        request_id="req-1",
        request=PurchaseRequest(item="widget", quantity=5, reason="stock low"),
    )
    assert cf.status == "RAISED"
    assert cf.verdicts == {}
    assert cf.writeups == []
    assert cf.route == []


def test_writeup_fields():
    wu = WriteUp(screen="injection", detail="hidden instruction", source_role="legal")
    assert wu.screen == "injection"
    assert wu.detail == "hidden instruction"
    assert wu.source_role == "legal"


# --- Seam 3: graph building ------------------------------------------------

def test_build_graph_routes_roles_in_registry_order():
    reg = load_registry(REGISTRY_PATH)
    compiled = build_graph(reg)
    graph = compiled.get_graph()

    nodes = set(graph.nodes)
    assert {"watcher", "procurement", "legal", "finance", "compliance", "done"} <= nodes

    edges = {(e.source, e.target) for e in graph.edges}
    assert ("__start__", "watcher") in edges
    assert ("watcher", "procurement") in edges
    assert ("procurement", "legal") in edges
    assert ("legal", "finance") in edges
    assert ("finance", "compliance") in edges
    assert ("compliance", "done") in edges
    assert ("done", "__end__") in edges


# --- Seam 4: terminal routing ----------------------------------------------

_STORES = {
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


def _llm_factory(name):
    from purchase_office.llm import FakeLLMClient

    return FakeLLMClient({"decision": "approve", "note": "ok"})


def test_dry_run_reaches_filed():
    reg = load_registry(REGISTRY_PATH)
    compiled = build_graph(reg, llm_factory=_llm_factory, stores=_STORES)
    result = compiled.invoke(_initial_state())
    assert result["status"] == "FILED"


def test_first_reject_routes_to_rejected():
    reg = load_registry(REGISTRY_PATH)

    def rejecting_llm(name):
        from purchase_office.llm import FakeLLMClient

        if name == "legal":
            return FakeLLMClient({"decision": "reject", "note": "declined"})
        return FakeLLMClient({"decision": "approve", "note": "ok"})

    compiled = build_graph(reg, llm_factory=rejecting_llm, stores=_STORES)
    result = compiled.invoke(_initial_state())
    assert result["status"] == "REJECTED"
