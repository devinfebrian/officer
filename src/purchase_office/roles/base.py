"""Role base class: identity, clearance, state projection, verdict writing."""

from typing import Any

from ..config import Clearance
from ..llm import LLMClient
from ..state import CaseFile, Verdict

FLOWING_FIELDS = {"request", "vendor", "quote"}


class Role:
    def __init__(
        self,
        name: str,
        identity: str,
        clearance: Clearance,
        tools: dict[str, Any],
        llm: LLMClient | None,
        stores: dict[str, Any] | None = None,
    ):
        self.name = name
        self.identity = identity
        self.clearance = clearance
        self.tools = tools
        self.llm = llm
        self.stores = stores or {}

    def project(self, state: CaseFile) -> dict[str, Any]:
        view = {}
        for field in self.clearance.read:
            if field in FLOWING_FIELDS and getattr(state, field, None) is not None:
                view[field] = getattr(state, field)
        return view

    def tool_results(self, state: CaseFile) -> dict[str, Any]:
        return {}

    def run(self, state: CaseFile) -> dict[str, Any]:
        view = self.project(state)
        tool_results = self.tool_results(state)
        prompt = self.build_prompt(view, tool_results)
        result = self.llm.complete(prompt, schema={})
        verdict = Verdict(role=self.name, **result)
        return {"verdicts": {**state.verdicts, self.name: verdict}}

    def build_prompt(self, view: dict[str, Any], tool_results: dict[str, Any] | None = None) -> str:
        return f"Role {self.name} reviews: {view} tools: {tool_results or {}}"
