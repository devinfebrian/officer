"""Compliance: checks the vendor against the sanctioned list."""

from typing import Any

from ..state import CaseFile
from .base import Role


class Compliance(Role):
    def tool_results(self, state: CaseFile) -> dict[str, Any]:
        return {
            "sanctioned": self.tools["check_sanctions"](self.stores["sanctions"], state.vendor.name)
        }
