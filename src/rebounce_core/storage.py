from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


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

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_memories_companion_status
    ON memories(companion_id, status);

CREATE INDEX IF NOT EXISTS idx_events_companion_created
    ON events(companion_id, created_at);
"""


class SQLiteStore:
    """Stage 0 durable storage.

    SQLite is used first because it is serverless and portable. A larger
    database can be introduced later behind the same domain contracts.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript(SCHEMA)

    def save_companion(self, identity: Any) -> None:
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

    def list_memories(self, companion_id: str) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM memories
                WHERE companion_id = ? AND status = 'active'
                ORDER BY importance DESC, created_at DESC
                """,
                (companion_id,),
            ).fetchall()
        return [dict(row) for row in rows]
