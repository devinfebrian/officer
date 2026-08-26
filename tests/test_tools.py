from purchase_office.tools import (
    check_clauses,
    check_quote,
    check_sanctions,
    check_stock,
    read_budget,
    read_contract,
    search_vendors,
    select_vendor,
)

INVENTORY = {
    "widget": {"stock": 3, "reorder_threshold": 5},
    "gadget": {"stock": 20, "reorder_threshold": 5},
}

VENDORS = [
    {
        "name": "Acme Supply",
        "item": "widget",
        "quote": 120.0,
        "contract": "Standard terms. Payment net 30.",
    },
    {
        "name": "Globex",
        "item": "widget",
        "quote": 95.0,
        "contract": "Standard terms. Payment net 30.",
    },
]

BUDGET = {"limit": 200.0}

SANCTIONS = ["Globex"]


def test_check_stock_reports_low_when_at_or_below_threshold():
    assert check_stock(INVENTORY, "widget")["low"] is True
    assert check_stock(INVENTORY, "gadget")["low"] is False


def test_check_stock_returns_stock_and_threshold():
    result = check_stock(INVENTORY, "widget")
    assert result == {
        "item": "widget",
        "stock": 3,
        "reorder_threshold": 5,
        "low": True,
    }


def test_search_vendors_returns_only_matching_item():
    names = search_vendors(VENDORS, "widget")
    assert names == ["Acme Supply", "Globex"]


def test_select_vendor_returns_a_vendor():
    vendor = select_vendor(VENDORS, "widget")
    assert vendor["name"] in {"Acme Supply", "Globex"}
    assert vendor["item"] == "widget"


def test_read_contract_returns_contract_text():
    assert read_contract(VENDORS[0]) == "Standard terms. Payment net 30."


def test_check_clauses_accepts_standard_terms():
    assert check_clauses(read_contract(VENDORS[0])) is True


def test_read_budget_returns_limit():
    assert read_budget(BUDGET) == {"limit": 200.0}


def test_check_quote_compares_against_budget():
    assert check_quote(BUDGET, 120.0) == {
        "limit": 200.0,
        "quote": 120.0,
        "within_budget": True,
    }
    assert check_quote(BUDGET, 250.0)["within_budget"] is False


def test_check_sanctions_flags_sanctioned_vendor():
    assert check_sanctions(SANCTIONS, "Globex") is True
    assert check_sanctions(SANCTIONS, "Acme Supply") is False
