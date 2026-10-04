from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from rebounce_core.advanced import (
    DeviceSyncManager,
    EmbodimentManager,
    LongRunningAgent,
    PhysicalWorldManager,
    SharedActivityManager,
    VisionManager,
)
from rebounce_core.identity import CompanionIdentity
from rebounce_core.permissions import ActionLevel
from rebounce_core.storage import SQLiteStore


class Stage10To15Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(Path(self.tmp.name) / "rebounce.db")
        self.identity = CompanionIdentity(user_id="u1", name="Nova")
        self.store.save_companion(self.identity)
        self.cid = self.identity.companion_id
        self.uid = self.identity.user_id

    def tearDown(self):
        self.tmp.cleanup()

    def allow(self, resource, level):
        from rebounce_core.capabilities import set_permission
        set_permission(self.store, str(self.cid), resource, True, level)

    def test_stage10_vision_is_ephemeral_and_hashes_capture(self):
        manager = VisionManager(self.store, self.uid, self.cid)
        with self.assertRaises(PermissionError):
            manager.start_session()
        self.allow("screen", 1)
        session = manager.start_session(minutes=5)
        context = manager.observe(session["id"], window_title="Browser", app_name="Chrome", observation="A task list is visible.", screenshot_b64="raw-image")
        self.assertTrue(context["content_hash"])
        self.assertNotIn("raw-image", str(context))
        manager.end_session(session["id"])
        self.assertFalse(manager.status()["active_session"])

    def test_stage11_durable_plan_jobs_checkpoint_recovery_and_delegation(self):
        self.allow("delegation", int(ActionLevel.REVERSIBLE))
        manager = LongRunningAgent(self.store, self.uid, self.cid)
        plan = manager.create_plan("Research", "Compare three approaches.")
        job = manager.add_job(plan["id"], "First step", "Collect approved sources.")
        with self.assertRaises(PermissionError):
            manager.run_next(plan["id"])
        manager.approve_plan(plan["id"], True)
        result = manager.run_next(plan["id"])
        self.assertEqual(result["status"], "checkpointed")
        self.assertEqual(len(manager.state()["checkpoints"]), 1)
        delegation = manager.delegate(job["id"], "researcher", "Bounded source collection")
        self.assertEqual(delegation["status"], "proposed")

    def test_stage12_device_sync_and_handoff(self):
        manager = DeviceSyncManager(self.store, self.uid, self.cid)
        device = manager.register("Pixel", "phone", "Android", ["chat", "voice"])
        event = manager.append_event(device["id"], "memory.updated", {"memory_id": "m1"})
        self.assertEqual(manager.pull_since(0)[0]["id"], event["id"])
        offline = manager.queue_offline(device["id"], "send_message", {"text": "later"})
        self.assertEqual(offline["status"], "queued")
        handoff = manager.handoff(device["id"], None, 5)
        self.assertTrue(handoff["token"])

    def test_stage13_embodiment_and_persistent_room(self):
        manager = EmbodimentManager(self.store, self.uid, self.cid)
        profile = manager.configure({"profile_name": "Nova 3D", "asset_kind": "vrm", "asset_ref": "avatar.vrm", "expression_set": "calm,joy", "animation_style": "expressive"})
        room = manager.room("Research Room", "glass")
        obj = manager.upsert_object("note", "Pinned idea", {"text": "hello"})
        self.assertEqual(profile["asset_kind"], "vrm")
        self.assertEqual(room["theme"], "glass")
        self.assertEqual(obj["kind"], "note")
        self.assertEqual(len(manager.state()["objects"]), 1)

    def test_stage14_shared_activities(self):
        manager = SharedActivityManager(self.store, self.uid, self.cid)
        activity = manager.create("study", "Signals revision")
        event = manager.add_event(activity["id"], "user", "started_topic", {"topic": "FFT"})
        self.assertEqual(event["activity_id"], activity["id"])
        finished = manager.update(activity["id"], "completed", {"score": 0.9})
        self.assertEqual(finished["status"], "completed")

    def test_stage15_physical_world_is_disabled_until_permitted_and_simulator_is_safe(self):
        manager = PhysicalWorldManager(self.store, self.uid, self.cid)
        device = manager.register_device("Desk light", "smart_home", "simulator", "desk", ["on", "off"])
        with self.assertRaises(PermissionError):
            manager.enable_device(device["id"], True)
        self.allow("physical_devices", 3)
        self.allow("smart_home", 3)
        enabled = manager.enable_device(device["id"], True)
        self.assertEqual(enabled["enabled"], 1)
        command = manager.command(device["id"], "on", {"brightness": 20}, 3, approved=False)
        self.assertEqual(command["status"], "pending_approval")
        resolved = manager.resolve_command(command["id"], True)
        self.assertEqual(resolved["status"], "simulated")


if __name__ == "__main__":
    unittest.main()
