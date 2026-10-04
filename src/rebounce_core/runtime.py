from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .events import Event, EventType
from .identity import CompanionIdentity
from .memory import MemoryEngine
from .models import ModelMessage, ModelResponse, ModelRole, ModelStreamChunk
from .permissions import PermissionPolicy
from .provider import ModelProvider
from .relationship import RelationshipEngine
from .storage import SQLiteStore


@dataclass(slots=True)
class RuntimeState:
    companion_id: str
    active_conversation_id: str | None = None
    phase: str = "idle"
    last_user_message_at: str | None = None
    last_assistant_message_at: str | None = None
    last_model: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    content: str
    event_id: str
    provider: str
    conversation_id: str
    model: str


class CompanionRuntime:
    def __init__(
        self,
        identity: CompanionIdentity,
        store: SQLiteStore,
        provider: ModelProvider,
        permissions: PermissionPolicy | None = None,
        memory: MemoryEngine | None = None,
        relationship: RelationshipEngine | None = None,
    ) -> None:
        self.identity = identity
        self.store = store
        self.provider = provider
        self.permissions = permissions or PermissionPolicy.safe_default()
        self.memory = memory or MemoryEngine(store)
        self.relationship = relationship or RelationshipEngine(store)
        self.state = RuntimeState(str(identity.companion_id))

    def _system_message(self, query: str) -> ModelMessage:
        text = (
            f"You are {self.identity.name}, an AI companion in ReBounce. "
            "Be honest that you are an AI. Preserve continuity. "
            "Do not claim actions or experiences you did not perform."
        )
        if self.identity.personality.strip():
            text += f" Personality guidance: {self.identity.personality.strip()}"

        memories = self.memory.context_for(self.identity.companion_id, query)
        if memories:
            text += "\n\nRelevant user memory:\n" + memories

        relationship = self.relationship.context_for(str(self.identity.companion_id))
        if relationship:
            text += "\n\nRelationship continuity:\n" + relationship

        return ModelMessage(ModelRole.SYSTEM, text)

    def _prepare_turn(
        self, content: str, conversation_id: str | None
    ) -> tuple[str, list[ModelMessage]]:
        if not content.strip():
            raise ValueError("content must not be empty")
        now = datetime.now(timezone.utc).isoformat()

        if conversation_id is None:
            conversation_id = str(uuid4())
            self.store.add_conversation(
                conversation_id, str(self.identity.companion_id), now
            )
        else:
            conversation = self.store.get_conversation(conversation_id)
            if conversation is None:
                raise ValueError("conversation_id does not exist")
            if str(conversation["companion_id"]) != str(self.identity.companion_id):
                raise ValueError("conversation_id belongs to another companion")

        self.store.save_message(
            str(uuid4()), conversation_id, ModelRole.USER.value, content, now
        )
        self.store.save_event(
            Event(
                type=EventType.USER_MESSAGE,
                user_id=self.identity.user_id,
                companion_id=self.identity.companion_id,
                data={"conversation_id": conversation_id},
            )
        )

        self.memory.process_user_message(self.identity, content, conversation_id)
        self.relationship.record_interaction(self.identity, content)

        messages = [self._system_message(content)]
        for row in self.store.list_messages(conversation_id):
            messages.append(ModelMessage(ModelRole(row["role"]), row["content"]))

        self.state.active_conversation_id = conversation_id
        self.state.phase = "responding"
        self.state.last_user_message_at = now
        return conversation_id, messages

    def _record_failure(self, conversation_id: str, exc: Exception) -> None:
        self.store.save_event(
            Event(
                type=EventType.MODEL_UNAVAILABLE,
                user_id=self.identity.user_id,
                companion_id=self.identity.companion_id,
                data={
                    "conversation_id": conversation_id,
                    "provider": self.provider.name,
                    "error": str(exc)[:500],
                },
            )
        )
        self.state.phase = "error"

    def _finish_response(
        self, conversation_id: str, response: ModelResponse
    ) -> RuntimeResult:
        now = datetime.now(timezone.utc).isoformat()
        self.store.save_message(
            str(uuid4()),
            conversation_id,
            ModelRole.ASSISTANT.value,
            response.content,
            now,
        )
        event = Event(
            type=EventType.ASSISTANT_MESSAGE,
            user_id=self.identity.user_id,
            companion_id=self.identity.companion_id,
            data={
                "conversation_id": conversation_id,
                "provider": response.provider_name,
                "model": response.model_name,
                "finish_reason": response.finish_reason,
            },
        )
        self.store.save_event(event)
        self.state.phase = "idle"
        self.state.last_assistant_message_at = now
        self.state.last_model = response.model_name
        return RuntimeResult(
            response.content,
            str(event.event_id),
            response.provider_name,
            conversation_id,
            response.model_name,
        )

    async def handle_user_message(
        self,
        content: str,
        *,
        conversation_id: str | None = None,
        model: str | None = None,
    ) -> RuntimeResult:
        conversation_id, messages = self._prepare_turn(content, conversation_id)
        try:
            response = await self.provider.generate(messages, model=model)
        except Exception as exc:
            self._record_failure(conversation_id, exc)
            raise
        return self._finish_response(conversation_id, response)

    async def stream_user_message(
        self,
        content: str,
        *,
        conversation_id: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:
        conversation_id, messages = self._prepare_turn(content, conversation_id)
        pieces: list[str] = []
        response_model = model or ""
        response_provider = self.provider.name
        finish_reason = "stop"

        try:
            async for chunk in self.provider.stream(messages, model=model):
                response_model = chunk.model_name or response_model
                response_provider = chunk.provider_name or response_provider
                finish_reason = chunk.finish_reason or finish_reason
                if chunk.content:
                    pieces.append(chunk.content)
                    yield chunk
        except Exception as exc:
            self._record_failure(conversation_id, exc)
            raise

        self._finish_response(
            conversation_id,
            ModelResponse(
                "".join(pieces),
                response_model or "unknown",
                response_provider,
                finish_reason,
            ),
        )
