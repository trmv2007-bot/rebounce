from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .events import Event, EventType
from .identity import CompanionIdentity
from .models import ModelMessage, ModelRole
from .permissions import PermissionPolicy
from .provider import ModelProvider
from .storage import SQLiteStore


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    content: str
    event_id: str
    provider: str


class CompanionRuntime:
    """Minimal Stage 0 companion lifecycle."""

    def __init__(
        self,
        identity: CompanionIdentity,
        store: SQLiteStore,
        provider: ModelProvider,
        permissions: PermissionPolicy | None = None,
    ) -> None:
        self.identity = identity
        self.store = store
        self.provider = provider
        self.permissions = permissions or PermissionPolicy.safe_default()

    async def handle_user_message(
        self,
        content: str,
        *,
        conversation_id: str | None = None,
        model: str | None = None,
    ) -> RuntimeResult:
        if not content.strip():
            raise ValueError("content must not be empty")

        now = datetime.now(timezone.utc).isoformat()

        if conversation_id is None:
            conversation_id = str(uuid4())
            self.store.add_conversation(
                conversation_id,
                str(self.identity.companion_id),
                now,
            )

        self.store.save_message(
            str(uuid4()),
            conversation_id,
            ModelRole.USER.value,
            content,
            now,
        )

        user_event = Event(
            type=EventType.USER_MESSAGE,
            user_id=self.identity.user_id,
            companion_id=self.identity.companion_id,
            data={"conversation_id": conversation_id},
        )
        self.store.save_event(user_event)

        response = await self.provider.generate(
            [ModelMessage(ModelRole.USER, content)],
            model=model,
        )

        self.store.save_message(
            str(uuid4()),
            conversation_id,
            ModelRole.ASSISTANT.value,
            response.content,
            datetime.now(timezone.utc).isoformat(),
        )

        assistant_event = Event(
            type=EventType.ASSISTANT_MESSAGE,
            user_id=self.identity.user_id,
            companion_id=self.identity.companion_id,
            data={
                "conversation_id": conversation_id,
                "provider": response.provider_name,
                "model": response.model_name,
            },
        )
        self.store.save_event(assistant_event)

        return RuntimeResult(
            content=response.content,
            event_id=str(assistant_event.event_id),
            provider=response.provider_name,
        )
