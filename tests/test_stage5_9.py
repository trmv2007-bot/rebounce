from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from rebounce_core.capabilities import (
    AttentionState,
    AutonomyManager,
    CuriosityEngine,
    ToolGateway,
    get_attention,
    load_policy,
    resolve_approval,
    set_attention,
    set_permission,
)
from rebounce_core.identity import CompanionIdentity
from rebounce_core.storage import SQLiteStore
from rebounce_core.voice import VoicePhase, VoiceSession


class Stage59Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(Path(self.tmp.name) / "rebounce.db")
        self.identity = CompanionIdentity("u1", "Nova")
        self.store.save_companion(self.identity)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_voice_session_turns_and_interruption(self) -> None:
        voice = VoiceSession()
        voice.start_listening()
        self.assertEqual(voice.phase, VoicePhase.LISTENING)
        voice.receive_transcript("hello", final=True)
        self.assertEqual(voice.phase, VoicePhase.THINKING)
        voice.start_speaking()
        voice.interrupt()
        self.assertEqual(voice.phase, VoicePhase.INTERRUPTED)
        self.assertEqual(voice.turns, 1)

    def test_attention_state_and_due_reminder(self) -> None:
        cid = str(self.identity.companion_id)
        set_attention(self.store, cid, {"activity": "available", "daily_budget": 2})
        manager = AutonomyManager(self.store, self.identity.user_id, self.identity.companion_id)
        due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        manager.add_reminder("Check ReBounce", due)
        created = manager.run_due()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["kind"], "reminder")
        self.assertEqual(manager.list_reminders()[0]["status"], "completed")

    def test_quiet_hours_save_proactive_work(self) -> None:
        cid = str(self.identity.companion_id)
        now = datetime.now().astimezone()
        start = (now - timedelta(minutes=1)).strftime("%H:%M")
        end = (now + timedelta(minutes=1)).strftime("%H:%M")
        if start == end:
            end = (now + timedelta(minutes=2)).strftime("%H:%M")
        set_attention(self.store, cid, {"activity": "available", "quiet_start": start, "quiet_end": end, "daily_budget": 2})
        manager = AutonomyManager(self.store, self.identity.user_id, self.identity.companion_id)
        due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        manager.add_reminder("Quiet reminder", due)
        created = manager.run_due()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["status"], "deferred")

    def test_tool_approval_gate(self) -> None:
        cid = str(self.identity.companion_id)
        root = Path(self.tmp.name) / "workspace"
        root.mkdir()
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO companion_settings(companion_id,key,value,updated_at) VALUES (?,?,?,?)",
                (cid, "filesystem.root", json.dumps(str(root)), datetime.now(timezone.utc).isoformat()),
            )
        set_permission(self.store, cid, "local_files", True, 3)
        gateway = ToolGateway(self.store, self.identity.user_id, self.identity.companion_id)
        first = gateway.execute("local_files.write", {"path": "hello.txt", "content": "hi"})
        self.assertEqual(first["status"], "approval_required")
        approval = resolve_approval(self.store, first["approval_id"], True)
        self.assertEqual(approval["status"], "approved")
        second = gateway.execute("local_files.write", {"path": "hello.txt", "content": "hi"}, approved=True)
        self.assertEqual(second["status"], "ok")
        self.assertEqual((root / "hello.txt").read_text(), "hi")

    def test_local_work_tools_are_reversible(self) -> None:
        gateway = ToolGateway(self.store, self.identity.user_id, self.identity.companion_id)
        note = gateway.execute("notes.create", {"title": "Idea", "content": "Build bounded curiosity"})
        self.assertEqual(note["status"], "ok")
        task = gateway.execute("tasks.create", {"title": "Ship Stage 9", "priority": 1})
        self.assertEqual(task["status"], "ok")
        self.assertTrue(task["result"]["id"])
        event = gateway.execute("calendar.create", {"title": "Demo", "start_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        self.assertEqual(event["status"], "ok")

    def test_curiosity_budget_and_interest_suggestion(self) -> None:
        cid = str(self.identity.companion_id)
        CuriosityEngine(self.store, self.identity.user_id, self.identity.companion_id).configure(True, 2)
        with self.store._connect() as con:
            con.execute(
                """INSERT INTO memories(id,companion_id,memory_type,content,source,confidence,importance,sensitivity,scope,status,created_at,metadata_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("m1", cid, "project", "I am building an AI companion", "user", .9, .9, "normal", "companion", "active", datetime.now(timezone.utc).isoformat(), "{}"),
            )
        engine = CuriosityEngine(self.store, self.identity.user_id, self.identity.companion_id)
        self.assertTrue(engine.suggest_query())
        self.assertEqual(engine.budget()["remaining"], 2)


if __name__ == "__main__":
    unittest.main()
