from pathlib import Path

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


def test_happy_path_ends_filed_with_four_verdicts_in_route_order():
    reg = load_registry(REGISTRY_PATH)
    llm_factory = lambda name: FakeLLMClient({"decision": "approve", "note": "ok"})
    compiled = build_graph(reg, llm_factory=llm_factory, stores=STORES)

    result = compiled.invoke(
        {
            "request_id": "req-1",
            "request": {"item": "widget", "quantity": 5, "reason": "stock low"},
        }
    )

    assert result["status"] == "FILED"
    assert list(result["verdicts"].keys()) == [
        "procurement",
        "legal",
        "finance",
        "compliance",
    ]
    assert all(v.decision == "approve" for v in result["verdicts"].values())


def test_happy_path_procurement_appends_vendor_and_quote():
    reg = load_registry(REGISTRY_PATH)
    llm_factory = lambda name: FakeLLMClient({"decision": "approve", "note": "ok"})
    compiled = build_graph(reg, llm_factory=llm_factory, stores=STORES)

    result = compiled.invoke(
        {
            "request_id": "req-1",
            "request": {"item": "widget", "quantity": 5, "reason": "stock low"},
        }
    )

    assert result["vendor"] is not None
    assert result["vendor"].name == "Acme Supply"
    assert result["quote"] is not None
    assert result["quote"].amount == 120.0
