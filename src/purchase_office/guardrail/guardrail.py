"""Guardrail: screens every inter-role message before it enters the Case File."""

from ..config import GuardrailConfig
from ..state import WriteUp
from . import screens as screen_functions


class Guardrail:
    def __init__(self, config: GuardrailConfig):
        self.config = config

    def check(self, sender: str, recipient: str, message: str, categories=None):
        for name in self.config.screens:
            detail = self._run_screen(name, recipient, message, categories)
            if detail is not None:
                return False, WriteUp(screen=name, detail=detail, source_role=sender)
        return True, None

    def _run_screen(self, name: str, recipient: str, message: str, categories=None):
        if name == "injection":
            return screen_functions.injection_screen(message)
        if name == "pii":
            return screen_functions.pii_screen(message)
        if name == "role_policy":
            allowed = self.config.policy.get(recipient)
            return screen_functions.role_policy_screen(message, allowed, categories)
        return None
