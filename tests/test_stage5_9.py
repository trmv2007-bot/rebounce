from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from rebounce_core.capabilities import (
    TOOL_SPECS,
    AttentionState,
    AutonomyManager,
    CuriosityEngine,
    ToolGateway,
    get_attention,
    load_policy,
    mcp_command_allowed,
    resolve_approval,
    set_attention,
    set_permission,
)
from rebounce_core.identity import CompanionIdentity
from rebounce_core.permissions import ActionLevel
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
        # Keep the window wide enough to survive slow CI runners crossing a minute boundary.
        start = (now - timedelta(minutes=2)).strftime("%H:%M")
        end = (now + timedelta(minutes=2)).strftime("%H:%M")
        set_attention(self.store, cid, {"activity": "available", "quiet_start": start, "quiet_end": end, "daily_budget": 2})
        manager = AutonomyManager(self.store, self.identity.user_id, self.identity.companion_id)
        due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        manager.add_reminder("Quiet reminder", due)
        created = manager.run_due()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["status"], "deferred")

    def _local_files_granted(self) -> Path:
        """Grant local_files at L3 with a sandbox under this test's temp dir."""
        cid = str(self.identity.companion_id)
        root = Path(self.tmp.name) / "workspace"
        root.mkdir(exist_ok=True)
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO companion_settings(companion_id,key,value,updated_at) VALUES (?,?,?,?)",
                (cid, "filesystem.root", json.dumps(str(root)), datetime.now(timezone.utc).isoformat()),
            )
        set_permission(self.store, cid, "local_files", True, 3)
        return root

    def test_tool_approval_gate(self) -> None:
        root = self._local_files_granted()
        gateway = ToolGateway(self.store, self.identity.user_id, self.identity.companion_id)
        args = {"path": "hello.txt", "content": "hi"}
        first = gateway.execute("local_files.write", args)
        self.assertEqual(first["status"], "approval_required")
        self.assertFalse((root / "hello.txt").exists())
        approval = resolve_approval(self.store, first["approval_id"], True)
        self.assertEqual(approval["status"], "approved")
        second = gateway.execute("local_files.write", args, approval_id=first["approval_id"])
        self.assertEqual(second["status"], "ok")
        self.assertEqual((root / "hello.txt").read_text(), "hi")

    def test_approval_must_be_resolved_single_use_and_arg_bound(self) -> None:
        self._local_files_granted()
        gateway = ToolGateway(self.store, self.identity.user_id, self.identity.companion_id)
        args = {"path": "a.txt", "content": "one"}
        queued = gateway.execute("local_files.write", args)
        approval_id = queued["approval_id"]

        # pending is not approved
        self.assertEqual(gateway.execute("local_files.write", args, approval_id=approval_id)["status"], "denied")

        resolve_approval(self.store, approval_id, True)
        # the approval covers these exact arguments only
        other = dict(args, content="two")
        self.assertEqual(gateway.execute("local_files.write", other, approval_id=approval_id)["status"], "denied")
        # an invented approval id grants nothing
        self.assertEqual(gateway.execute("local_files.write", args, approval_id="0" * 32)["status"], "denied")

        self.assertEqual(gateway.execute("local_files.write", args, approval_id=approval_id)["status"], "ok")
        # consumed, so it cannot be replayed
        self.assertEqual(gateway.execute("local_files.write", args, approval_id=approval_id)["status"], "denied")

    def test_permission_and_approval_flags_are_not_python_truthiness(self) -> None:
        cid = str(self.identity.companion_id)
        self.assertEqual(set_permission(self.store, cid, "local_files", "false", 3)["allowed"], False)
        self.assertEqual(set_permission(self.store, cid, "local_files", "off", 3)["allowed"], False)
        self.assertEqual(set_permission(self.store, cid, "local_files", "yes", 3)["allowed"], True)
        with self.assertRaises(ValueError):
            set_permission(self.store, cid, "local_files", "maybe", 3)
        with self.assertRaises(ValueError):
            set_permission(self.store, cid, "local_files", True, 9)
        with self.assertRaises(ValueError):
            set_permission(self.store, cid, "not_a_real_resource", True, 3)

    def test_mcp_commands_need_an_explicit_allowlist(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(mcp_command_allowed("anything"))
        with patch.dict(os.environ, {"REBOUNCE_MCP_ALLOWLIST": "echo"}):
            self.assertTrue(mcp_command_allowed("echo"))
            self.assertTrue(mcp_command_allowed("C:\\tools\\echo.exe"))
            self.assertFalse(mcp_command_allowed("curl"))
            self.assertFalse(mcp_command_allowed("echo; rm -rf /"))
            self.assertFalse(mcp_command_allowed(""))

    def test_mcp_tools_require_approval(self) -> None:
        specs = {spec.name: spec for spec in TOOL_SPECS}
        self.assertGreaterEqual(specs["mcp.list_tools"].level, ActionLevel.APPROVAL_REQUIRED)
        self.assertGreaterEqual(specs["mcp.call"].level, ActionLevel.APPROVAL_REQUIRED)

        cid = str(self.identity.companion_id)
        set_permission(self.store, cid, "mcp", True, 3)
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO mcp_servers(id,companion_id,name,command,args_json,enabled,created_at,updated_at) VALUES (?,?,?,?,?,1,?,?)",
                ("s1", cid, "test", "echo", "[]", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
            )
        gateway = ToolGateway(self.store, self.identity.user_id, self.identity.companion_id)
        result = gateway.execute("mcp.list_tools", {"server_id": "s1"})
        self.assertEqual(result["status"], "approval_required")

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
