from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from .events import Event, EventType
from .identity import CompanionIdentity
from .storage import SQLiteStore


class RelationshipEngine:
    _STOP = set(
        "the and that this with from have just what did tell about your you are was "
        "were for but not how can could would should into on my i me we to a an of "
        "in is it be or as at do so".split()
    )

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def record_interaction(self, identity: CompanionIdentity, text: str) -> dict:
        now = datetime.now(timezone.utc)
        profile = self.store.get_relationship(str(identity.companion_id))
        day = now.date().isoformat()
        prior_day = (profile.get("last_interaction_at") or "")[:10]

        profile["interactions"] = int(profile["interactions"]) + 1
        profile["first_interaction_at"] = profile["first_interaction_at"] or now.isoformat()
        profile["last_interaction_at"] = now.isoformat()
        profile["active_days"] = int(profile.get("active_days", 0)) + (prior_day != day)

        topics = dict(profile.get("topics", {}))
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower()):
            if word not in self._STOP:
                topics[word] = int(topics.get(word, 0)) + 1
        profile["topics"] = dict(
            sorted(topics.items(), key=lambda item: item[1], reverse=True)[:15]
        )

        signals = {
            "be concise": ("directness", 0.08),
            "keep it short": ("directness", 0.08),
            "more detail": ("verbosity", 0.08),
            "be warmer": ("warmth", 0.08),
            "more humor": ("humor", 0.08),
        }
        lowered = text.lower()
        for signal, (field, delta) in signals.items():
            if signal in lowered:
                profile[field] = min(1.0, float(profile.get(field, 0.5)) + delta)

        self.store.upsert_relationship(profile)
        if profile["interactions"] == 1:
            self.add_milestone(
                identity,
                "First conversation",
                f"{identity.name} and you started ReBounce together.",
            )
        return profile

    def context_for(self, companion_id: str) -> str:
        profile = self.store.get_relationship(companion_id)
        parts = [
            f"Shared interaction count: {profile['interactions']}",
            f"Active days: {profile['active_days']}",
        ]
        topics = list(sorted(profile.get("topics", {}).items(), key=lambda item: item[1], reverse=True)[:5])
        if topics:
            parts.append("Recurring topics: " + ", ".join(k for k, _ in topics))
        goals = [g["title"] for g in self.store.list_goals(companion_id) if g["status"] == "active"][:3]
        if goals:
            parts.append("Active goals: " + ", ".join(goals))

        prefs = []
        if profile["directness"] > 0.58:
            prefs.append("prefer concise/direct communication")
        if profile["verbosity"] > 0.62:
            prefs.append("prefer more detail")
        if profile["warmth"] > 0.68:
            prefs.append("respond warmly")
        if profile["humor"] > 0.62:
            prefs.append("use light humor when appropriate")
        if prefs:
            parts.append("Interaction preferences: " + ", ".join(prefs))
        return "\n".join("- " + item for item in parts)

    def add_milestone(self, identity: CompanionIdentity, title: str, description: str = "") -> dict:
        milestone = {
            "id": str(uuid.uuid4()),
            "companion_id": str(identity.companion_id),
            "title": title.strip(),
            "description": description.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.store.add_milestone(milestone)
        return milestone

    def add_goal(self, identity: CompanionIdentity, title: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        goal = {
            "id": str(uuid.uuid4()),
            "companion_id": str(identity.companion_id),
            "title": title.strip(),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        self.store.add_goal(goal)
        self.store.save_event(
            Event(
                type=EventType.GOAL_CHANGED,
                user_id=identity.user_id,
                companion_id=identity.companion_id,
                data={"goal_id": goal["id"], "status": "active"},
            )
        )
        return goal

    def update_goal(self, goal_id: str, status: str) -> None:
        self.store.update_goal(goal_id, status)

    def add_commitment(self, identity: CompanionIdentity, title: str, due_at: str | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        commitment = {
            "id": str(uuid.uuid4()),
            "companion_id": str(identity.companion_id),
            "title": title.strip(),
            "due_at": due_at,
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
        self.store.add_commitment(commitment)
        self.store.save_event(
            Event(
                type=EventType.COMMITMENT_CREATED,
                user_id=identity.user_id,
                companion_id=identity.companion_id,
                data={"commitment_id": commitment["id"]},
            )
        )
        return commitment
