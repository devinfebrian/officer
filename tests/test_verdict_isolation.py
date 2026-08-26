from purchase_office.config import Clearance
from purchase_office.llm import FakeLLMClient
from purchase_office.roles.base import Role
from purchase_office.state import CaseFile, PurchaseRequest, Verdict


def _role(name, decision="approve", read=None):
    return Role(
        name=name,
        identity="key",
        clearance=Clearance(tools=[], read=read or []),
        tools={},
        llm=FakeLLMClient(scripted={"decision": decision, "note": "ok"}),
    )


def _casefile(verdicts=None):
    return CaseFile(
        request_id="req-1",
        request=PurchaseRequest(item="widget", quantity=5, reason="stock low"),
        verdicts=verdicts or {},
    )


def test_run_writes_only_its_own_slot():
    role = _role("legal")
    result = role.run(_casefile())
    assert set(result["verdicts"].keys()) == {"legal"}


def test_run_merges_into_existing_verdicts():
    existing = {"procurement": Verdict(role="procurement", decision="approve", note="ok")}
    role = _role("legal")
    result = role.run(_casefile(verdicts=existing))

    assert set(result["verdicts"].keys()) == {"procurement", "legal"}
    assert result["verdicts"]["procurement"] == existing["procurement"]
    assert result["verdicts"]["legal"].role == "legal"
    assert result["verdicts"]["legal"].decision == "approve"


def test_run_does_not_touch_other_roles_writing_same_state():
    existing = {"finance": Verdict(role="finance", decision="reject", note="no")}
    role = _role("legal")
    result = role.run(_casefile(verdicts=existing))
    assert result["verdicts"]["finance"].decision == "reject"
