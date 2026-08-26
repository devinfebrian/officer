"""Deterministic tool functions over seeded stores.

Every tool is a pure function of its inputs so tests can inject small
fixtures. The stores (inventory, vendors, budget, sanctions) are seeded by the
demo layer (S6); the roles call these functions with whatever store handle
they are given.
"""


def check_stock(inventory: dict, item: str) -> dict:
    entry = inventory[item]
    stock = entry["stock"]
    threshold = entry["reorder_threshold"]
    return {
        "item": item,
        "stock": stock,
        "reorder_threshold": threshold,
        "low": stock <= threshold,
    }


def search_vendors(vendors: list[dict], item: str) -> list[str]:
    return [v["name"] for v in vendors if v["item"] == item]


def select_vendor(vendors: list[dict], item: str) -> dict:
    candidates = [v for v in vendors if v["item"] == item]
    return min(candidates, key=lambda v: v["quote"])


def read_contract(vendor) -> str:
    if hasattr(vendor, "contract"):
        return vendor.contract
    return vendor["contract"]


def check_clauses(contract: str) -> bool:
    return "Standard terms" in contract


def read_budget(budget: dict) -> dict:
    return {"limit": budget["limit"]}


def check_quote(budget: dict, quote: float) -> dict:
    return {
        "limit": budget["limit"],
        "quote": quote,
        "within_budget": quote <= budget["limit"],
    }


def check_sanctions(sanctions: list[str], vendor_name: str) -> bool:
    return vendor_name in sanctions
