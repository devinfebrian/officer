from purchase_office.config import Clearance
from purchase_office.llm import FakeLLMClient
from purchase_office.roles.base import Role
from purchase_office.roles.procurement import Procurement
from purchase_office.state import CaseFile, PurchaseRequest, Quote, Vendor, Verdict


def _casefile():
    return CaseFile(
        request_id="req-1",
        request=PurchaseRequest(item="widget", quantity=5, reason="stock low"),
    )


def test_specialist_message_is_verdict_note():
    role = Role(
        name="legal",
        identity="key",
        clearance=Clearance(tools=[], read=[]),
        tools={},
        llm=None,
    )
    update = {"verdicts": {"legal": Verdict(role="legal", decision="approve", note="contract ok")}}
    assert role.message_for(_casefile(), update) == "contract ok"


def test_specialist_message_empty_without_verdict():
    role = Role(
        name="legal",
        identity="key",
        clearance=Clearance(tools=[], read=[]),
        tools={},
        llm=None,
    )
    assert role.message_for(_casefile(), {}) == ""


def test_procurement_message_is_vendor_contract():
    role = Procurement(
        name="procurement",
        identity="key",
        clearance=Clearance(tools=[], read=[]),
        tools={},
        llm=FakeLLMClient({"decision": "approve", "note": "ok"}),
    )
    vendor = Vendor(name="Acme", item="widget", quote=120.0, contract="Standard terms.")
    update = {"vendor": vendor, "quote": Quote(vendor="Acme", amount=120.0)}
    assert role.message_for(_casefile(), update) == "Standard terms."
