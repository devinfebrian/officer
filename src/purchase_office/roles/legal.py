"""Legal: reads the contract and checks standard clauses."""

from typing import Any

from ..state import CaseFile
from .base import Role


class Legal(Role):
    def tool_results(self, state: CaseFile) -> dict[str, Any]:
        contract = self.tools["read_contract"](state.vendor)
        return {"clauses_ok": self.tools["check_clauses"](contract)}
