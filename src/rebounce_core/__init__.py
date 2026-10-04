"""ReBounce companion core.

Stage 0 intentionally keeps the core dependency-light and cross-platform.
"""

from .events import Event, EventType
from .identity import CompanionIdentity
from .models import ModelMessage, ModelResponse, ModelRole
from .permissions import ActionLevel, PermissionPolicy
from .runtime import CompanionRuntime, RuntimeResult
from .storage import SQLiteStore

__all__ = [
    "ActionLevel",
    "CompanionIdentity",
    "CompanionRuntime",
    "Event",
    "EventType",
    "ModelMessage",
    "ModelResponse",
    "ModelRole",
    "PermissionPolicy",
    "RuntimeResult",
    "SQLiteStore",
]
