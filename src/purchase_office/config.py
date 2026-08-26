"""Registry loading: YAML -> typed models, failing fast on bad config."""

from pathlib import Path

import yaml
from pydantic import BaseModel

KNOWN_ROLES = {
    "watcher",
    "procurement",
    "legal",
    "finance",
    "compliance",
    "done",
}

KNOWN_TOOLS = {
    "check_stock",
    "search_vendors",
    "select_vendor",
    "read_contract",
    "check_clauses",
    "read_budget",
    "check_quote",
    "check_sanctions",
}


class ConfigError(Exception):
    """Raised when the Registry references an unknown role or tool."""


class Clearance(BaseModel):
    tools: list[str] = []
    read: list[str] = []


class RoleConfig(BaseModel):
    name: str
    identity: str
    next: list[str] = []
    clearance: Clearance


class GuardrailConfig(BaseModel):
    screens: list[str] = []
    policy: dict[str, list[str]] = {}


class Registry(BaseModel):
    roles: list[RoleConfig]
    guardrail: GuardrailConfig


def _validate(roles: list[RoleConfig]) -> None:
    for role in roles:
        for nxt in role.next:
            if nxt not in KNOWN_ROLES:
                raise ConfigError(f"unknown next role '{nxt}' on role '{role.name}'")
        for tool in role.clearance.tools:
            if tool not in KNOWN_TOOLS:
                raise ConfigError(f"unknown tool '{tool}' on role '{role.name}'")


def load_registry(path: str | Path) -> Registry:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    roles = []
    for name, spec in raw["roles"].items():
        roles.append(
            RoleConfig(
                name=name,
                identity=spec["identity"],
                next=spec.get("next", []),
                clearance=Clearance(**spec.get("clearance", {})),
            )
        )

    _validate(roles)

    guardrail = GuardrailConfig(**raw.get("guardrail", {}))
    return Registry(roles=roles, guardrail=guardrail)
