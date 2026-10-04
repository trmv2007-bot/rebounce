from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ModelRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: ModelRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("model message content must not be empty")


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    model_name: str
    provider_name: str
    finish_reason: str = "stop"
