"""Procurement: selects a vendor and appends the vendor + quote."""

from typing import Any

from ..state import CaseFile, Quote, Vendor, Verdict
from .base import Role


class Procurement(Role):
    def run(self, state: CaseFile) -> dict[str, Any]:
        item = state.request.item
        vendor = self.tools["select_vendor"](self.stores["vendors"], item)
        vendor_model = Vendor(
            name=vendor["name"],
            item=vendor["item"],
            quote=vendor["quote"],
            contract=vendor["contract"],
        )
        quote_model = Quote(vendor=vendor["name"], amount=vendor["quote"])

        view = {"request": state.request, "vendor": vendor_model, "quote": quote_model}
        prompt = self.build_prompt(view)
        result = self.llm.complete(prompt, schema={})
        verdict = Verdict(role=self.name, **result)
        return {
            "vendor": vendor_model,
            "quote": quote_model,
            "verdicts": {**state.verdicts, self.name: verdict},
        }

    def message_for(self, state: CaseFile, update: dict[str, Any]) -> str:
        vendor = update.get("vendor")
        return vendor.contract if vendor else ""
