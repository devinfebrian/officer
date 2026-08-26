"""Roles: the desks in the office."""

from .base import Role
from .compliance import Compliance
from .finance import Finance
from .legal import Legal
from .procurement import Procurement
from .watcher import Watcher

__all__ = ["Role", "Watcher", "Procurement", "Legal", "Finance", "Compliance"]
