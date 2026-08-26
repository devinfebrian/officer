"""Watcher: observes stock and raises the Purchase Request."""

from typing import Any

from ..state import CaseFile
from .base import Role


class Watcher(Role):
    def run(self, state: CaseFile) -> dict[str, Any]:
        return {}
