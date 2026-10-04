from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .events import Event, EventType
from .identity import CompanionIdentity
from .storage import SQLiteStore


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    memory_type: str
    content: str
    key: str
    confidence: float = 0.95
    importance: float = 0.7
    metadata: dict[str, Any] | None = None


class MemoryEngine:
    """Structured Stage 2 memory lifecycle.

    Stage 2 keeps extraction dependency-free and deterministic while leaving
    room for a model-assisted extractor later.
    """

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def extract_candidates(self, text: str) -> list[MemoryCandidate]:
        text = text.strip()
        candidates: list[MemoryCandidate] = []

        def add(
            memory_type: str,
            content: str,
            key: str,
            importance: float = 0.7,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            value = content.strip(" .!?\n")
            if value:
                candidates.append(
                    MemoryCandidate(
                        memory_type=memory_type,
                        content=value,
                        key=key,
                        metadata=metadata,
                        importance=importance,
                    )
                )

        patterns = [
            (r"\bmy name is ([^.!?]+)", "fact", "user_name", 0.95, None),
            (r"\bi (?:live|am living) in ([^.!?]+)", "fact", "location", 0.85, None),
            (r"\bi(?:'m| am) from ([^.!?]+)", "fact", "origin", 0.8, None),
            (r"\bi (?:like|love) ([^.!?]+)", "preference", "likes", 0.7, None),
            (
                r"\bi (?:don't like|dislike|hate) ([^.!?]+)",
                "preference",
                "dislikes",
                0.75,
                None,
            ),
            (r"\bi prefer ([^.!?]+)", "preference", "preferred", 0.8, None),
            (
                r"\bmy favorite ([^.!?]+?) is ([^.!?]+)",
                "preference",
                "favorite",
                0.8,
                None,
            ),
            (
                r"\bi(?:'m| am) working on ([^.!?]+)",
                "project",
                "active_project",
                0.85,
                None,
            ),
            (r"\bmy goal is ([^.!?]+)", "goal", "goal", 0.9, None),
            (r"\bremember that ([^.!?]+)", "fact", "explicit_memory", 0.9, None),
        ]

        for pattern, memory_type, key, importance, metadata in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            if memory_type == "preference" and key == "favorite":
                content = f"{match.group(1).strip()}: {match.group(2).strip()}"
            else:
                content = match.group(0)
            add(memory_type, content, key, importance, metadata)

        return candidates

    def add(
        self,
        identity: CompanionIdentity,
        candidate: MemoryCandidate,
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        for memory in self.store.list_all_memories(str(identity.companion_id)):
            metadata = _load_metadata(memory["metadata_json"])
            if metadata.get("key") != candidate.key:
                continue
            if memory["content"].strip().lower() == candidate.content.strip().lower():
                return memory
            self.store.supersede_memory(memory["id"])

        memory = {
            "id": str(uuid.uuid4()),
            "companion_id": str(identity.companion_id),
            "memory_type": candidate.memory_type,
            "content": candidate.content,
            "source": "user",
            "source_ref": source_ref,
            "confidence": candidate.confidence,
            "importance": candidate.importance,
            "sensitivity": "normal",
            "scope": "companion",
            "status": "active",
            "created_at": now,
            "observed_at": now,
            "last_confirmed_at": now,
            "metadata": {
                "key": candidate.key,
                "provenance": "user",
                **(candidate.metadata or {}),
            },
        }
        self.store.save_memory(memory)
        self.store.save_event(
            Event(
                type=EventType.MEMORY_CREATED,
                user_id=identity.user_id,
                companion_id=identity.companion_id,
                data={
                    "memory_id": memory["id"],
                    "memory_type": memory["memory_type"],
                },
            )
        )
        return memory

    def process_user_message(
        self,
        identity: CompanionIdentity,
        text: str,
        source_ref: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self.add(identity, candidate, source_ref)
            for candidate in self.extract_candidates(text)
        ]

    def retrieve(
        self,
        companion_id: str,
        query: str,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        memories = self.store.list_all_memories(str(companion_id))
        query_words = set(re.findall(r"[a-z0-9]{3,}", query.lower()))

        def score(memory: dict[str, Any]) -> float:
            words = set(re.findall(r"[a-z0-9]{3,}", memory["content"].lower()))
            overlap = len(query_words & words)
            return (
                overlap * 3
                + float(memory["importance"]) * 2
                + float(memory["confidence"])
            )

        return sorted(memories, key=score, reverse=True)[:limit]

    def context_for(
        self,
        companion_id: str,
        query: str,
        limit: int = 8,
    ) -> str:
        rows = self.retrieve(companion_id, query, limit)
        if not rows:
            return ""
        return "\n".join(
            f"- {row['memory_type']}: {row['content']}" for row in rows
        )

    def correct(self, memory_id: str, new_content: str) -> dict[str, Any]:
        memory = self.store.get_memory(memory_id)
        if memory is None:
            raise ValueError("memory not found")
        metadata = _load_metadata(memory["metadata_json"])
        history = metadata.setdefault("correction_history", [])
        history.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "from": memory["content"],
            }
        )
        metadata["provenance"] = "user"
        self.store.update_memory(
            memory_id,
            new_content.strip(),
            metadata,
            float(memory["confidence"]),
            float(memory["importance"]),
        )
        self.store.save_event(
            Event(
                type=EventType.MEMORY_UPDATED,
                user_id="",
                companion_id=__import__("uuid").UUID(memory["companion_id"]),
                data={"memory_id": memory_id, "action": "correct"},
            )
        )
        return self.store.get_memory(memory_id) or {}

    def forget(self, memory_id: str) -> None:
        self.store.delete_memory(memory_id)

    def consolidate(self, companion_id: str) -> int:
        seen: set[tuple[str, str]] = set()
        removed = 0
        for memory in self.store.list_all_memories(str(companion_id)):
            key = (
                memory["memory_type"],
                memory["content"].strip().lower(),
            )
            if key in seen:
                self.store.delete_memory(memory["id"])
                removed += 1
            else:
                seen.add(key)
        return removed


def _load_metadata(value: str) -> dict[str, Any]:
    import json

    try:
        result = json.loads(value)
    except Exception:
        return {}
    return result if isinstance(result, dict) else {}
