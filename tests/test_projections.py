from purchase_office.config import Clearance
from purchase_office.roles.base import Role
from purchase_office.state import CaseFile, PurchaseRequest, Quote, Vendor, Verdict


def _populated_casefile():
    return CaseFile(
        request_id="req-1",
        request=PurchaseRequest(item="widget", quantity=5, reason="stock low"),
        vendor=Vendor(name="Acme", item="widget", quote=120.0, contract="terms"),
        quote=Quote(vendor="Acme", amount=120.0),
        verdicts={"legal": Verdict(role="legal", decision="approve", note="ok")},
    )


def _role(read_fields, name="testrole"):
    return Role(
        name=name,
        identity="key",
        clearance=Clearance(tools=[], read=read_fields),
        tools={},
        llm=None,
    )


def test_projection_returns_only_cleared_fields():
    role = _role(["request", "vendor"])
    projected = role.project(_populated_casefile())
    assert set(projected.keys()) == {"request", "vendor"}


def test_projection_never_includes_verdicts_or_writeups():
    role = _role(["request", "quote"])
    projected = role.project(_populated_casefile())
    assert "verdicts" not in projected
    assert "writeups" not in projected


def test_projection_ignores_unknown_read_fields():
    role = _role(["request", "ghost"])
    projected = role.project(_populated_casefile())
    assert set(projected.keys()) == {"request"}


def test_projection_returns_empty_for_no_clearance():
    role = _role([])
    assert role.project(_populated_casefile()) == {}
