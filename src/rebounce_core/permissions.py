from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ActionLevel(IntEnum):
    NO_ACTION = 0
    INFORMATIONAL = 1
    REVERSIBLE = 2
    APPROVAL_REQUIRED = 3
    SENSITIVE_APPROVAL = 4
    PROHIBITED = 5


@dataclass(frozen=True, slots=True)
class PermissionRule:
    resource: str
    max_level: ActionLevel = ActionLevel.INFORMATIONAL
    allowed: bool = True


class PermissionPolicy:
    """Deterministic permission gate.

    The model may propose an action, but this policy makes the final decision.
    """

    def __init__(self, rules: tuple[PermissionRule, ...] = ()) -> None:
        self._rules = {rule.resource: rule for rule in rules}

    def decide(self, resource: str, requested_level: ActionLevel) -> bool:
        rule = self._rules.get(resource)
        if rule is None:
            return False
        if not rule.allowed or rule.max_level == ActionLevel.PROHIBITED:
            return False
        return requested_level <= rule.max_level

    def describe(self, resource: str) -> dict[str, object]:
        rule = self._rules.get(resource)
        if rule is None:
            return {
                "resource": resource,
                "allowed": False,
                "max_level": ActionLevel.NO_ACTION,
            }
        return {
            "resource": resource,
            "allowed": rule.allowed,
            "max_level": rule.max_level,
        }

    @classmethod
    def safe_default(cls) -> "PermissionPolicy":
        return cls((
            PermissionRule("conversation", ActionLevel.INFORMATIONAL, True),
            PermissionRule("memory", ActionLevel.REVERSIBLE, True),
            PermissionRule("local_files", ActionLevel.NO_ACTION, False),
            PermissionRule("browser", ActionLevel.NO_ACTION, False),
            PermissionRule("github", ActionLevel.NO_ACTION, False),
            PermissionRule("mcp", ActionLevel.NO_ACTION, False),
            PermissionRule("notes", ActionLevel.REVERSIBLE, True),
            PermissionRule("tasks", ActionLevel.REVERSIBLE, True),
            PermissionRule("calendar", ActionLevel.REVERSIBLE, True),
            PermissionRule("projects", ActionLevel.REVERSIBLE, True),
            PermissionRule("voice", ActionLevel.REVERSIBLE, True),
            PermissionRule("presence", ActionLevel.REVERSIBLE, True),
            PermissionRule("email", ActionLevel.NO_ACTION, False),
            PermissionRule("payments", ActionLevel.PROHIBITED, False),
        ))
