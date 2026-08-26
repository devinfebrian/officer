"""Orchestrator: builds the office floor (StateGraph) from the Registry."""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from .config import Registry
from .llm import LLMClient
from .roles import Compliance, Finance, Legal, Procurement, Watcher
from .state import CaseFile
from . import tools as tool_functions

ROLE_CLASSES = {
    "watcher": Watcher,
    "procurement": Procurement,
    "legal": Legal,
    "finance": Finance,
    "compliance": Compliance,
}


def _terminal(state: CaseFile):
    rejected = any(v.decision == "reject" for v in state.verdicts.values())
    return {"status": "REJECTED" if rejected else "FILED"}


def _make_role_node(role):
    def node(state: CaseFile):
        return role.run(state)

    return node


def build_graph(
    registry: Registry,
    llm_factory: Callable[[str], LLMClient] | None = None,
    stores: dict[str, Any] | None = None,
):
    stores = stores or {}
    graph = StateGraph(CaseFile)

    for role_cfg in registry.roles:
        cls = ROLE_CLASSES[role_cfg.name]
        role = cls(
            name=role_cfg.name,
            identity=role_cfg.identity,
            clearance=role_cfg.clearance,
            tools={t: getattr(tool_functions, t) for t in role_cfg.clearance.tools},
            llm=llm_factory(role_cfg.name) if llm_factory else None,
            stores=stores,
        )
        graph.add_node(role_cfg.name, _make_role_node(role))

    graph.add_node("done", _terminal)

    graph.add_edge(START, registry.roles[0].name)
    for role_cfg in registry.roles:
        for nxt in role_cfg.next:
            graph.add_edge(role_cfg.name, nxt)
    graph.add_edge("done", END)

    return graph.compile()
