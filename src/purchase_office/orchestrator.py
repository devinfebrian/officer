"""Orchestrator: builds the office floor (StateGraph) from the Registry."""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from . import tools as tool_functions
from .config import Registry
from .guardrail.guardrail import Guardrail
from .llm import LLMClient
from .roles import Compliance, Finance, Legal, Procurement, Watcher
from .state import CaseFile

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


def _make_role_node(role, guardrail: Guardrail, recipient: str):
    def node(state: CaseFile):
        update = role.run(state)
        message = role.message_for(state, update)
        ok, writeup = guardrail.check(role.name, recipient, message)
        if not ok:
            return {
                "status": "QUARANTINED",
                "writeups": [*state.writeups, writeup],
            }
        return update

    return node


def _route_after_role(state: CaseFile):
    return "end" if state.status == "QUARANTINED" else "continue"


def build_graph(
    registry: Registry,
    llm_factory: Callable[[str], LLMClient] | None = None,
    stores: dict[str, Any] | None = None,
):
    stores = stores or {}
    guardrail = Guardrail(registry.guardrail)
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
        recipient = role_cfg.next[0] if role_cfg.next else "done"
        graph.add_node(role_cfg.name, _make_role_node(role, guardrail, recipient))

    graph.add_node("done", _terminal)

    graph.add_edge(START, registry.roles[0].name)
    for role_cfg in registry.roles:
        recipient = role_cfg.next[0] if role_cfg.next else "done"
        graph.add_conditional_edges(
            role_cfg.name,
            _route_after_role,
            {"end": END, "continue": recipient},
        )

    graph.add_edge("done", END)

    return graph.compile()
