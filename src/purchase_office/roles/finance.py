"""Finance: checks the quote against the budget."""

from typing import Any

from ..state import CaseFile
from .base import Role


class Finance(Role):
    def tool_results(self, state: CaseFile) -> dict[str, Any]:
        return {
            "budget": self.tools["read_budget"](self.stores["budget"]),
            "quote_check": self.tools["check_quote"](self.stores["budget"], state.quote.amount),
        }
