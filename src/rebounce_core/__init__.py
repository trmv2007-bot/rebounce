"""ReBounce companion core."""

from .api import ReBounceHTTPServer, create_local_api
from .events import Event, EventType
from .identity import CompanionIdentity
from .models import ModelMessage, ModelResponse, ModelRole, ModelStreamChunk
from .permissions import ActionLevel, PermissionPolicy
from .provider import (
    ModelProvider,
    ModelProviderError,
    OpenAICompatibleProvider,
    StubModelProvider,
)
from .runtime import CompanionRuntime, RuntimeResult, RuntimeState
from .storage import SQLiteStore

__all__ = [
    "ActionLevel",
    "CompanionIdentity",
    "CompanionRuntime",
    "Event",
    "EventType",
    "ModelMessage",
    "ModelProvider",
    "ModelProviderError",
    "ModelResponse",
    "ModelRole",
    "ModelStreamChunk",
    "OpenAICompatibleProvider",
    "PermissionPolicy",
    "ReBounceHTTPServer",
    "RuntimeResult",
    "RuntimeState",
    "SQLiteStore",
    "StubModelProvider",
    "create_local_api",
]
