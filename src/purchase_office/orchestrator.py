"""Orchestrator: builds the office floor (StateGraph) from the Registry."""

from langgraph.graph import END, START, StateGraph

from .config import Registry
from .state import CaseFile


def _stub(state: CaseFile):
    return {}


def _terminal(state: CaseFile):
    rejected = any(v.decision == "reject" for v in state.verdicts.values())
    return {"status": "REJECTED" if rejected else "FILED"}


def build_graph(registry: Registry):
    graph = StateGraph(CaseFile)

    for role in registry.roles:
        graph.add_node(role.name, _stub)
    graph.add_node("done", _terminal)

    graph.add_edge(START, registry.roles[0].name)
    for role in registry.roles:
        for nxt in role.next:
            graph.add_edge(role.name, nxt)
    graph.add_edge("done", END)

    return graph.compile()
