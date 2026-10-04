from __future__ import annotations

import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from rebounce_core.api import create_local_api
from rebounce_core.identity import CompanionIdentity
from rebounce_core.models import ModelMessage, ModelResponse, ModelRole, ModelStreamChunk
from rebounce_core.provider import OpenAICompatibleProvider, StubModelProvider
from rebounce_core.runtime import CompanionRuntime
from rebounce_core.storage import SQLiteStore


class RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.calls: list[list[ModelMessage]] = []

    async def generate(self, messages, *, model=None):
        self.calls.append(list(messages))
        return ModelResponse(
            content=f"reply to: {messages[-1].content}",
            model_name=model or "recording-model",
            provider_name=self.name,
        )

    async def _stream_impl(self, messages, *, model=None):
        self.calls.append(list(messages))
        yield ModelStreamChunk(
            content=f"stream reply to: {messages[-1].content}",
            model_name=model or "recording-model",
            provider_name=self.name,
        )

    def stream(self, messages, *, model=None):
        return self._stream_impl(messages, model=model)


class FakeResponse:
    def __init__(self, body: bytes | list[bytes]) -> None:
        self.body = body
        self.closed = False

    def read(self):
        if isinstance(self.body, list):
            return b"".join(self.body)
        return self.body

    def readline(self):
        if not isinstance(self.body, list):
            return self.body
        if not self.body:
            return b""
        return self.body.pop(0)

    def close(self):
        self.closed = True


class Stage1Tests(unittest.TestCase):
    def test_restart_preserves_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "rebounce.db"
            original = CompanionIdentity(
                user_id="user-1",
                name="Nova",
                personality="calm and direct",
            )
            SQLiteStore(db).save_companion(original)

            restarted_store = SQLiteStore(db)
            restored = restarted_store.get_companion(original.companion_id)

            self.assertIsNotNone(restored)
            assert restored is not None
            self.assertEqual(restored.companion_id, original.companion_id)
            self.assertEqual(restored.name, "Nova")
            self.assertEqual(restored.personality, "calm and direct")

    def test_runtime_reuses_persisted_conversation_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "rebounce.db")
            identity = CompanionIdentity(user_id="user-1", name="Nova")
            store.save_companion(identity)
            provider = RecordingProvider()
            runtime = CompanionRuntime(identity, store, provider)

            first = asyncio.run(runtime.handle_user_message("My favorite language is Python."))
            asyncio.run(
                runtime.handle_user_message(
                    "What did I just tell you?",
                    conversation_id=first.conversation_id,
                )
            )

            second_call = provider.calls[1]
            self.assertEqual(second_call[0].role, ModelRole.SYSTEM)
            self.assertEqual(second_call[1].content, "My favorite language is Python.")
            self.assertEqual(second_call[2].role, ModelRole.ASSISTANT)
            self.assertEqual(second_call[3].content, "What did I just tell you?")

    def test_streaming_persists_complete_assistant_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "rebounce.db")
            identity = CompanionIdentity(user_id="user-1", name="Nova")
            store.save_companion(identity)
            runtime = CompanionRuntime(identity, store, RecordingProvider())

            async def collect() -> list[ModelStreamChunk]:
                return [chunk async for chunk in runtime.stream_user_message("hello")]

            chunks = asyncio.run(collect())
            self.assertEqual(
                "".join(chunk.content for chunk in chunks),
                "stream reply to: hello",
            )
            rows = store.list_messages(runtime.state.active_conversation_id or "")
            self.assertEqual(rows[-1]["role"], "assistant")
            self.assertEqual(rows[-1]["content"], "stream reply to: hello")
            self.assertEqual(runtime.state.phase, "idle")

    def test_openai_compatible_generate_parses_response(self) -> None:
        payload = {
            "model": "local-model",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "hello from local model",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
        fake = FakeResponse(json.dumps(payload).encode())
        provider = OpenAICompatibleProvider(
            "http://127.0.0.1:8080/v1",
            default_model="local-model",
        )

        with patch(
            "rebounce_core.provider.urllib.request.urlopen",
            return_value=fake,
        ):
            response = asyncio.run(
                provider.generate([ModelMessage(ModelRole.USER, "hello")])
            )

        self.assertEqual(response.content, "hello from local model")
        self.assertEqual(response.provider_name, "openai-compatible")
        self.assertTrue(fake.closed)

    def test_openai_compatible_stream_parses_sse(self) -> None:
        lines = [
            b'data: {"model":"local-model","choices":[{"delta":{"content":"hello "},"finish_reason":null}]}\n\n',
            b'data: {"model":"local-model","choices":[{"delta":{"content":"world"},"finish_reason":"stop"}]}\n\n',
            b"data: [DONE]\n\n",
        ]
        fake = FakeResponse(lines)
        provider = OpenAICompatibleProvider(
            "http://127.0.0.1:8080/v1",
            default_model="local-model",
        )

        async def collect():
            return [
                chunk
                async for chunk in provider.stream(
                    [ModelMessage(ModelRole.USER, "hello")]
                )
            ]

        with patch(
            "rebounce_core.provider.urllib.request.urlopen",
            return_value=fake,
        ):
            chunks = asyncio.run(collect())

        self.assertEqual("".join(chunk.content for chunk in chunks), "hello world")
        self.assertEqual(chunks[-1].finish_reason, "stop")
        self.assertTrue(fake.closed)

    def test_local_api_create_identity_and_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "rebounce.db")
            server = create_local_api(store, StubModelProvider())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"

                with urlopen(f"{base}/health") as response:
                    health = json.loads(response.read().decode())
                    self.assertEqual(response.status, 200)
                self.assertEqual(health["stage"], 1)

                create_req = Request(
                    f"{base}/v1/companions",
                    data=json.dumps(
                        {"user_id": "user-1", "name": "Nova"}
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(create_req) as response:
                    created = json.loads(response.read().decode())
                    self.assertEqual(response.status, 201)

                companion_id = created["companion_id"]
                with urlopen(f"{base}/v1/companions/{companion_id}") as response:
                    restored = json.loads(response.read().decode())
                    self.assertEqual(response.status, 200)
                self.assertEqual(restored["name"], "Nova")

                chat_req = Request(
                    f"{base}/v1/companions/{companion_id}/chat",
                    data=json.dumps({"content": "hello"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(chat_req) as response:
                    result = json.loads(response.read().decode())
                    self.assertEqual(response.status, 200)

                self.assertIn("Stage 1", result["content"])
                self.assertEqual(result["provider"], "stub")

                stream_req = Request(
                    f"{base}/v1/companions/{companion_id}/chat",
                    data=json.dumps({"content": "stream me", "stream": True}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(stream_req) as response:
                    stream_body = response.read().decode()
                    self.assertEqual(response.status, 200)

                events = [
                    json.loads(line[6:])
                    for line in stream_body.splitlines()
                    if line.startswith("data: ")
                ]
                self.assertTrue(any(event.get("content") for event in events))
                self.assertTrue(events[-1]["done"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
