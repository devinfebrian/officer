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


def _make_terminal(audit):
    def terminal(state: CaseFile):
        rejected = any(v.decision == "reject" for v in state.verdicts.values())
        status = "REJECTED" if rejected else "FILED"
        if audit:
            audit.append(
                request_id=state.request_id, role="office", action="status", status=status
            )
        return {"status": status}

    return terminal


def _make_role_node(role, guardrail: Guardrail, recipient: str, audit):
    def node(state: CaseFile):
        if audit:
            detail = ""
            if role.name == "watcher" and state.request is not None:
                detail = (
                    f"{state.request.quantity} × {state.request.item} — {state.request.reason}"
                )
            audit.append(
                request_id=state.request_id,
                role=role.name,
                action="enter",
                status="ok",
                detail=detail,
            )
        update = role.run(state)
        message = role.message_for(state, update)
        # A desk's own verdict note is internal_notes; only data-bearing
        # updates (a vendor contract, a quote) are content-scanned.
        verdict_only = "verdicts" in update and not ({"vendor", "quote"} & set(update))
        categories = {"internal_notes"} if verdict_only else None
        ok, writeup = guardrail.check(role.name, recipient, message, categories)
        if audit:
            audit.append(
                request_id=state.request_id,
                role="guardrail",
                action="screen",
                status="pass" if ok else "fail",
                detail=writeup.screen if writeup else "",
            )
        if not ok:
            if audit:
                audit.append(
                    request_id=state.request_id,
                    role="guardrail",
                    action="writeup",
                    status="open",
                    detail=writeup.detail,
                )
                audit.append(
                    request_id=state.request_id,
                    role="office",
                    action="status",
                    status="QUARANTINED",
                )
            return {
                "status": "QUARANTINED",
                "writeups": [*state.writeups, writeup],
            }
        verdict = update.get("verdicts", {}).get(role.name)
        if verdict and audit:
            audit.append(
                request_id=state.request_id,
                role=role.name,
                action="verdict",
                status=verdict.decision,
                detail=verdict.note,
            )
        return update

    return node


def _route_after_role(state: CaseFile):
    return "end" if state.status == "QUARANTINED" else "continue"


def build_graph(
    registry: Registry,
    llm_factory: Callable[[str], LLMClient] | None = None,
    stores: dict[str, Any] | None = None,
    audit=None,
    checkpointer=None,
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
        graph.add_node(role_cfg.name, _make_role_node(role, guardrail, recipient, audit))

    graph.add_node("done", _make_terminal(audit))

    graph.add_edge(START, registry.roles[0].name)
    for role_cfg in registry.roles:
        recipient = role_cfg.next[0] if role_cfg.next else "done"
        graph.add_conditional_edges(
            role_cfg.name,
            _route_after_role,
            {"end": END, "continue": recipient},
        )

    graph.add_edge("done", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()
