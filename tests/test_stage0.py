import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path

from rebounce_core.identity import CompanionIdentity
from rebounce_core.permissions import ActionLevel, PermissionPolicy
from rebounce_core.provider import StubModelProvider
from rebounce_core.runtime import CompanionRuntime
from rebounce_core.storage import SQLiteStore


class Stage0Tests(unittest.TestCase):
    def test_identity_requires_name(self) -> None:
        with self.assertRaises(ValueError):
            CompanionIdentity(user_id="user-1", name="")

    def test_permission_policy_is_deterministic(self) -> None:
        policy = PermissionPolicy.safe_default()
        self.assertTrue(policy.decide("conversation", ActionLevel.INFORMATIONAL))
        self.assertTrue(policy.decide("memory", ActionLevel.REVERSIBLE))
        self.assertFalse(policy.decide("browser", ActionLevel.INFORMATIONAL))
        self.assertFalse(policy.decide("payments", ActionLevel.SENSITIVE_APPROVAL))

    def test_runtime_persists_messages_and_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "rebounce.db"
            identity = CompanionIdentity(user_id="user-1", name="Nova")
            store = SQLiteStore(db)
            store.save_companion(identity)

            runtime = CompanionRuntime(
                identity=identity,
                store=store,
                provider=StubModelProvider(),
            )

            result = asyncio.run(runtime.handle_user_message("Hello"))

            self.assertEqual(result.provider, "stub")
            self.assertIn("Stage 0", result.content)

            with sqlite3.connect(db) as con:
                message_count = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                event_count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]

            self.assertEqual(message_count, 2)
            self.assertEqual(event_count, 2)


if __name__ == "__main__":
    unittest.main()
