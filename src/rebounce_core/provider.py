from __future__ import annotations

from typing import Protocol, Sequence

from .models import ModelMessage, ModelResponse


class ModelProvider(Protocol):
    """Provider-neutral model interface."""

    @property
    def name(self) -> str:
        ...

    async def generate(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        ...


class StubModelProvider:
    """Deterministic Stage 0 provider used only for wiring/tests."""

    @property
    def name(self) -> str:
        return "stub"

    async def generate(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        del messages
        return ModelResponse(
            content="[Stage 0] Companion runtime is connected. Model provider not configured.",
            model_name=model or "stub",
            provider_name=self.name,
        )
