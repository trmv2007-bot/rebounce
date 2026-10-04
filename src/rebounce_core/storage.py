from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from .identity import CompanionIdentity


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    relationship_style TEXT NOT NULL DEFAULT 'companion',
    personality TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    source_ref TEXT,
    confidence REAL NOT NULL DEFAULT 0.5,
    importance REAL NOT NULL DEFAULT 0.5,
    sensitivity TEXT NOT NULL DEFAULT 'normal',
    scope TEXT NOT NULL DEFAULT 'companion',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    observed_at TEXT,
    last_confirmed_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permissions (
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    resource TEXT NOT NULL,
    allowed INTEGER NOT NULL DEFAULT 0,
    max_level INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (companion_id, resource)
);

CREATE TABLE IF NOT EXISTS relationship_state (
    companion_id TEXT PRIMARY KEY REFERENCES companions(id) ON DELETE CASCADE,
    interactions INTEGER NOT NULL DEFAULT 0,
    first_interaction_at TEXT,
    last_interaction_at TEXT,
    active_days INTEGER NOT NULL DEFAULT 0,
    directness REAL NOT NULL DEFAULT 0.5,
    verbosity REAL NOT NULL DEFAULT 0.5,
    warmth REAL NOT NULL DEFAULT 0.6,
    humor REAL NOT NULL DEFAULT 0.5,
    topics_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS milestones (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commitments (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    due_at TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companion_settings (
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (companion_id, key)
);

CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    due_at TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'reminder',
    recurrence TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proactive_queue (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    source_ref TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS curiosity_items (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    project_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    priority INTEGER NOT NULL DEFAULT 2,
    due_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT,
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_approvals (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    args_json TEXT NOT NULL,
    requested_level INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS mcp_servers (
    id TEXT PRIMARY KEY,
    companion_id TEXT NOT NULL REFERENCES companions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    command TEXT NOT NULL,
    args_json TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_memories_companion_status
    ON memories(companion_id, status);

CREATE INDEX IF NOT EXISTS idx_events_companion_created
    ON events(companion_id, created_at);
"""


class SQLiteStore:
    """Stage 2–4 durable SQLite store."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript(SCHEMA)

    def save_companion(self, identity: CompanionIdentity) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO companions
                (id, user_id, name, relationship_style, personality, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(identity.companion_id),
                    identity.user_id,
                    identity.name,
                    identity.relationship_style,
                    identity.personality,
                    identity.created_at.isoformat(),
                ),
            )

    def update_companion(
        self,
        companion_id: str | UUID,
        name: str,
        personality: str,
        relationship_style: str | None = None,
    ) -> None:
        with self._connect() as con:
            if relationship_style is None:
                con.execute(
                    "UPDATE companions SET name = ?, personality = ? WHERE id = ?",
                    (name, personality, str(companion_id)),
                )
            else:
                con.execute(
                    """
                    UPDATE companions
                    SET name = ?, personality = ?, relationship_style = ?
                    WHERE id = ?
                    """,
                    (name, personality, relationship_style, str(companion_id)),
                )

    def list_companions(self, user_id: str) -> list[CompanionIdentity]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM companions WHERE user_id = ? ORDER BY created_at",
                (user_id,),
            ).fetchall()
        return [self._identity(row) for row in rows]

    def get_companion(self, companion_id: str | UUID) -> CompanionIdentity | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM companions WHERE id = ?",
                (str(companion_id),),
            ).fetchone()
        return self._identity(row) if row else None

    @staticmethod
    def _identity(row: sqlite3.Row) -> CompanionIdentity:
        return CompanionIdentity(
            user_id=str(row["user_id"]),
            name=str(row["name"]),
            companion_id=UUID(str(row["id"])),
            relationship_style=str(row["relationship_style"]),
            personality=str(row["personality"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )

    def add_conversation(
        self, conversation_id: str, companion_id: str, created_at: str
    ) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO conversations(id, companion_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, companion_id, created_at, created_at),
            )

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_conversations(
        self, companion_id: str | UUID, limit: int = 50
    ) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM conversations
                WHERE companion_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (str(companion_id), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        created_at: str,
    ) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO messages(id, conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, conversation_id, role, content, created_at),
            )
            con.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (created_at, conversation_id),
            )

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_event(self, event: Any) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO events(id, companion_id, event_type, data_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    str(event.companion_id),
                    event.type.value if hasattr(event.type, "value") else str(event.type),
                    json.dumps(event.data, ensure_ascii=False),
                    event.created_at.isoformat(),
                ),
            )

    def list_events(
        self, companion_id: str | UUID, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM events
                WHERE companion_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (str(companion_id), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_memory(self, memory: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO memories(
                    id, companion_id, memory_type, content, source, source_ref,
                    confidence, importance, sensitivity, scope, status,
                    created_at, observed_at, last_confirmed_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory["id"],
                    memory["companion_id"],
                    memory["memory_type"],
                    memory["content"],
                    memory["source"],
                    memory.get("source_ref"),
                    float(memory.get("confidence", 0.5)),
                    float(memory.get("importance", 0.5)),
                    memory.get("sensitivity", "normal"),
                    memory.get("scope", "companion"),
                    memory.get("status", "active"),
                    memory["created_at"],
                    memory.get("observed_at"),
                    memory.get("last_confirmed_at"),
                    json.dumps(memory.get("metadata", {}), ensure_ascii=False),
                ),
            )

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return dict(row) if row else None

    def search_memories(
        self,
        companion_id: str | UUID,
        query: str | None = None,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM memories WHERE companion_id = ? AND status = 'active'"
        args: list[Any] = [str(companion_id)]
        if memory_type:
            sql += " AND memory_type = ?"
            args.append(memory_type)
        if query:
            sql += " AND (content LIKE ? OR metadata_json LIKE ?)"
            q = f"%{query}%"
            args.extend([q, q])
        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        args.append(limit)
        with self._connect() as con:
            rows = con.execute(sql, args).fetchall()
        return [dict(row) for row in rows]

    def list_all_memories(self, companion_id: str | UUID) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM memories
                WHERE companion_id = ? AND status = 'active'
                ORDER BY importance DESC, created_at DESC
                """,
                (str(companion_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any],
        confidence: float,
        importance: float,
    ) -> None:
        with self._connect() as con:
            con.execute(
                """
                UPDATE memories
                SET content = ?, metadata_json = ?, confidence = ?,
                    importance = ?, last_confirmed_at = ?, status = 'active'
                WHERE id = ?
                """,
                (
                    content,
                    json.dumps(metadata, ensure_ascii=False),
                    confidence,
                    importance,
                    datetime.now().astimezone().isoformat(),
                    memory_id,
                ),
            )

    def supersede_memory(self, memory_id: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE memories SET status = 'superseded' WHERE id = ?",
                (memory_id,),
            )

    def delete_memory(self, memory_id: str) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    def get_relationship(self, companion_id: str | UUID) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM relationship_state WHERE companion_id = ?",
                (str(companion_id),),
            ).fetchone()
        if row:
            data = dict(row)
            data["topics"] = json.loads(data.pop("topics_json") or "{}")
            return data
        return {
            "companion_id": str(companion_id),
            "interactions": 0,
            "first_interaction_at": None,
            "last_interaction_at": None,
            "active_days": 0,
            "directness": 0.5,
            "verbosity": 0.5,
            "warmth": 0.6,
            "humor": 0.5,
            "topics": {},
        }

    def upsert_relationship(self, profile: dict[str, Any]) -> None:
        now = profile.get("updated_at") or datetime.now().astimezone().isoformat()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO relationship_state(
                    companion_id, interactions, first_interaction_at,
                    last_interaction_at, active_days, directness, verbosity,
                    warmth, humor, topics_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(companion_id) DO UPDATE SET
                    interactions = excluded.interactions,
                    first_interaction_at = excluded.first_interaction_at,
                    last_interaction_at = excluded.last_interaction_at,
                    active_days = excluded.active_days,
                    directness = excluded.directness,
                    verbosity = excluded.verbosity,
                    warmth = excluded.warmth,
                    humor = excluded.humor,
                    topics_json = excluded.topics_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile["companion_id"],
                    profile["interactions"],
                    profile.get("first_interaction_at"),
                    profile.get("last_interaction_at"),
                    profile.get("active_days", 0),
                    profile.get("directness", 0.5),
                    profile.get("verbosity", 0.5),
                    profile.get("warmth", 0.6),
                    profile.get("humor", 0.5),
                    json.dumps(profile.get("topics", {}), ensure_ascii=False),
                    profile.get("created_at", now),
                    now,
                ),
            )

    def add_milestone(self, milestone: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO milestones(id, companion_id, title, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    milestone["id"],
                    milestone["companion_id"],
                    milestone["title"],
                    milestone.get("description", ""),
                    milestone["created_at"],
                ),
            )

    def list_milestones(self, companion_id: str | UUID, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM milestones
                WHERE companion_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (str(companion_id), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_goal(self, goal: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO goals(id, companion_id, title, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    goal["id"],
                    goal["companion_id"],
                    goal["title"],
                    goal.get("status", "active"),
                    goal["created_at"],
                    goal["updated_at"],
                ),
            )

    def list_goals(self, companion_id: str | UUID) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM goals
                WHERE companion_id = ?
                ORDER BY updated_at DESC
                """,
                (str(companion_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_goal(self, goal_id: str, status: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().astimezone().isoformat(), goal_id),
            )

    def add_commitment(self, commitment: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO commitments(
                    id, companion_id, title, due_at, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    commitment["id"],
                    commitment["companion_id"],
                    commitment["title"],
                    commitment.get("due_at"),
                    commitment.get("status", "open"),
                    commitment["created_at"],
                    commitment["updated_at"],
                ),
            )

    def list_commitments(self, companion_id: str | UUID) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM commitments
                WHERE companion_id = ?
                ORDER BY updated_at DESC
                """,
                (str(companion_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_data(self, companion_id: str | UUID) -> dict[str, Any]:
        identity = self.get_companion(companion_id)
        if identity is None:
            raise ValueError("companion not found")
        conversations = self.list_conversations(companion_id, 500)
        return {
            "version": 1,
            "exported_at": datetime.now().astimezone().isoformat(),
            "companion": {
                "user_id": identity.user_id,
                "name": identity.name,
                "companion_id": str(identity.companion_id),
                "relationship_style": identity.relationship_style,
                "personality": identity.personality,
                "created_at": identity.created_at.isoformat(),
            },
            "conversations": conversations,
            "messages": [
                message
                for conversation in conversations
                for message in self.list_messages(conversation["id"])
            ],
            "memories": self.list_all_memories(companion_id),
            "relationship": self.get_relationship(companion_id),
            "milestones": self.list_milestones(companion_id, 500),
            "goals": self.list_goals(companion_id),
            "commitments": self.list_commitments(companion_id),
            "events": self.list_events(companion_id, 500),
        }
