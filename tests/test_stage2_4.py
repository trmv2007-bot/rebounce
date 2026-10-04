from __future__ import annotations

import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from rebounce_core.api import create_local_api
from rebounce_core.identity import CompanionIdentity
from rebounce_core.memory import MemoryCandidate, MemoryEngine
from rebounce_core.models import ModelMessage, ModelResponse, ModelRole
from rebounce_core.provider import StubModelProvider
from rebounce_core.relationship import RelationshipEngine
from rebounce_core.runtime import CompanionRuntime
from rebounce_core.storage import SQLiteStore


class RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.calls = []

    async def generate(self, messages, *, model=None):
        self.calls.append(list(messages))
        return ModelResponse("remembered reply", model or "recording", self.name)

    def stream(self, messages, *, model=None):
        async def empty():
            if False:
                yield None
        return empty()


class Stage24Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "r.db"
        self.store = SQLiteStore(self.db)
        self.identity = CompanionIdentity("u1", "Nova")

    def tearDown(self):
        self.tmp.cleanup()

    def test_memory_extract_retrieve_correct_forget(self):
        engine = MemoryEngine(self.store)
        candidates = engine.extract_candidates("I prefer concise answers. I am working on ReBounce.")
        self.assertTrue(any(c.key == "preferred" for c in candidates))
        self.assertTrue(any(c.key == "active_project" for c in candidates))

        self.store.save_companion(self.identity)
        added = engine.process_user_message(self.identity, "I prefer concise answers.")
        self.assertEqual(len(added), 1)
        self.assertEqual(
            len(engine.retrieve(str(self.identity.companion_id), "what style do I like?")),
            1,
        )

        engine.correct(added[0]["id"], "I prefer concise but detailed answers.")
        self.assertEqual(
            self.store.get_memory(added[0]["id"])["content"],
            "I prefer concise but detailed answers.",
        )
        engine.forget(added[0]["id"])
        self.assertIsNone(self.store.get_memory(added[0]["id"]))

    def test_contradiction_preserves_history(self):
        engine = MemoryEngine(self.store)
        self.store.save_companion(self.identity)
        engine.add(
            self.identity,
            MemoryCandidate("preference", "I like tea", "likes"),
        )
        engine.add(
            self.identity,
            MemoryCandidate("preference", "I like coffee", "likes"),
        )
        self.assertEqual(
            len(self.store.list_all_memories(str(self.identity.companion_id))),
            1,
        )
        with self.store._connect() as con:
            superseded = con.execute(
                "SELECT COUNT(*) FROM memories WHERE status = 'superseded'"
            ).fetchone()[0]
        self.assertEqual(superseded, 1)

    def test_relationship_tracks_interactions_goals_and_milestone(self):
        self.store.save_companion(self.identity)
        engine = RelationshipEngine(self.store)
        profile = engine.record_interaction(
            self.identity,
            "I am studying Python and working on ReBounce.",
        )
        self.assertEqual(profile["interactions"], 1)
        self.assertGreaterEqual(profile["active_days"], 1)
        self.assertTrue(
            self.store.list_milestones(str(self.identity.companion_id))
        )

        goal = engine.add_goal(self.identity, "Ship Stage 4")
        self.assertEqual(goal["status"], "active")
        engine.update_goal(goal["id"], "completed")
        self.assertEqual(
            self.store.list_goals(str(self.identity.companion_id))[0]["status"],
            "completed",
        )

    def test_runtime_injects_memory_and_relationship_context(self):
        self.store.save_companion(self.identity)
        MemoryEngine(self.store).add(
            self.identity,
            MemoryCandidate("fact", "User is building ReBounce", "project"),
        )
        provider = RecordingProvider()
        runtime = CompanionRuntime(
            self.identity,
            self.store,
            provider,
            relationship=RelationshipEngine(self.store),
        )
        asyncio.run(runtime.handle_user_message("How is my project going?"))
        system = "\n".join(
            m.content for m in provider.calls[0] if m.role == ModelRole.SYSTEM
        )
        self.assertIn("User is building ReBounce", system)
        self.assertIn("Shared interaction count", system)

    def test_export_contains_core_state(self):
        self.store.save_companion(self.identity)
        data = self.store.export_data(str(self.identity.companion_id))
        self.assertIn("memories", data)
        self.assertIn("relationship", data)
        self.assertEqual(data["companion"]["name"], "Nova")

    def test_dashboard_api_and_assets(self):
        self.store.save_companion(self.identity)
        server = create_local_api(self.store, StubModelProvider())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(base + "/health") as response:
                self.assertEqual(json.loads(response.read())["stage"], 4)
            with urlopen(base + "/") as response:
                self.assertIn(b"ReBounce", response.read())
            with urlopen(base + "/assets/app.js") as response:
                self.assertIn(b"New chat", response.read())
            with urlopen(
                base + f"/v1/companions/{self.identity.companion_id}/dashboard"
            ) as response:
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
