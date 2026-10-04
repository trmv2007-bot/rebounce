from __future__ import annotations

import asyncio
import json
from argparse import ArgumentParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from uuid import UUID

from .identity import CompanionIdentity
from .provider import ModelProvider, OpenAICompatibleProvider, StubModelProvider
from .runtime import CompanionRuntime
from .storage import SQLiteStore


_MAX_BODY_BYTES = 1024 * 1024


class ReBounceHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        store: SQLiteStore,
        provider: ModelProvider,
    ) -> None:
        self.store = store
        self.provider = provider
        super().__init__(server_address, ReBounceRequestHandler)


class ReBounceRequestHandler(BaseHTTPRequestHandler):
    server_version = "ReBounce/1.0"

    @property
    def rebounce_server(self) -> ReBounceHTTPServer:
        return self.server  # type: ignore[return-value]

    def _write_json(self, status: int | HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError as exc:
            raise ValueError("Content-Length must be an integer") from exc
        if length > _MAX_BODY_BYTES:
            raise ValueError("request body is too large")
        body = self.rfile.read(length)
        if not body:
            return {}
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _runtime_for(self, companion_id: str) -> CompanionRuntime | None:
        try:
            UUID(companion_id)
        except ValueError:
            return None
        identity = self.rebounce_server.store.get_companion(companion_id)
        if identity is None:
            return None
        return CompanionRuntime(
            identity,
            self.rebounce_server.store,
            self.rebounce_server.provider,
        )

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(
                HTTPStatus.OK,
                {"status": "ok", "service": "rebounce", "stage": 1},
            )
            return

        parts = [part for part in self.path.split("/") if part]
        if len(parts) == 3 and parts[:2] == ["v1", "companions"]:
            identity = self.rebounce_server.store.get_companion(parts[2])
            if identity is None:
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "companion not found"})
                return
            self._write_json(
                HTTPStatus.OK,
                {
                    "companion_id": str(identity.companion_id),
                    "user_id": identity.user_id,
                    "name": identity.name,
                    "relationship_style": identity.relationship_style,
                    "personality": identity.personality,
                    "created_at": identity.created_at.isoformat(),
                },
            )
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        parts = [part for part in self.path.split("/") if part]
        if self.path == "/v1/companions":
            try:
                identity = CompanionIdentity(
                    user_id=str(payload["user_id"]),
                    name=str(payload["name"]),
                    personality=str(payload.get("personality", "")),
                    relationship_style=str(
                        payload.get("relationship_style", "companion")
                    ),
                )
            except (KeyError, TypeError, ValueError) as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            try:
                self.rebounce_server.store.save_companion(identity)
            except Exception as exc:
                self._write_json(HTTPStatus.CONFLICT, {"error": str(exc)})
                return
            self._write_json(
                HTTPStatus.CREATED,
                {"companion_id": str(identity.companion_id), "name": identity.name},
            )
            return

        if len(parts) == 4 and parts[:2] == ["v1", "companions"] and parts[3] == "chat":
            runtime = self._runtime_for(parts[2])
            if runtime is None:
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "companion not found"})
                return

            content = payload.get("content")
            if not isinstance(content, str) or not content.strip():
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "content must be a non-empty string"},
                )
                return

            conversation_id = payload.get("conversation_id")
            if conversation_id is not None and not isinstance(conversation_id, str):
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "conversation_id must be a string"},
                )
                return

            model = payload.get("model")
            if model is not None and not isinstance(model, str):
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "model must be a string"},
                )
                return

            if bool(payload.get("stream", False)):
                self._stream_chat(runtime, content, conversation_id, model)
                return

            try:
                result = asyncio.run(
                    runtime.handle_user_message(
                        content,
                        conversation_id=conversation_id,
                        model=model,
                    )
                )
            except Exception as exc:
                self._write_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
                return

            self._write_json(
                HTTPStatus.OK,
                {
                    "content": result.content,
                    "provider": result.provider,
                    "model": result.model,
                    "conversation_id": result.conversation_id,
                    "event_id": result.event_id,
                },
            )
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _stream_chat(
        self,
        runtime: CompanionRuntime,
        content: str,
        conversation_id: str | None,
        model: str | None,
    ) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        async def emit() -> None:
            try:
                async for chunk in runtime.stream_user_message(
                    content,
                    conversation_id=conversation_id,
                    model=model,
                ):
                    self._write_sse(
                        {
                            "content": chunk.content,
                            "provider": chunk.provider_name,
                            "model": chunk.model_name,
                            "finish_reason": chunk.finish_reason,
                        }
                    )
                self._write_sse(
                    {
                        "done": True,
                        "conversation_id": runtime.state.active_conversation_id,
                        "model": runtime.state.last_model,
                    }
                )
            except Exception as exc:
                self._write_sse({"error": str(exc)[:500], "done": True})

        asyncio.run(emit())

    def _write_sse(self, payload: dict[str, Any]) -> None:
        line = (
            f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        ).encode("utf-8")
        self.wfile.write(line)
        self.wfile.flush()

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_local_api(
    store: SQLiteStore,
    provider: ModelProvider,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> ReBounceHTTPServer:
    """Create a localhost-only Stage 1 API server."""
    return ReBounceHTTPServer((host, port), store, provider)


def main() -> None:
    import os

    parser = ArgumentParser(description="Run the local ReBounce Stage 1 API")
    parser.add_argument("--db", default=os.getenv("REBOUNCE_DB", "rebounce.db"))
    parser.add_argument("--host", default=os.getenv("REBOUNCE_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("REBOUNCE_PORT", "4100")),
    )
    parser.add_argument("--model-url", default=os.getenv("REBOUNCE_MODEL_URL"))
    parser.add_argument("--model", default=os.getenv("REBOUNCE_MODEL"))
    parser.add_argument("--api-key", default=os.getenv("REBOUNCE_MODEL_API_KEY"))
    args = parser.parse_args()

    if args.model_url:
        if not args.model:
            parser.error("--model is required when --model-url is supplied")
        provider: ModelProvider = OpenAICompatibleProvider(
            args.model_url,
            api_key=args.api_key,
            default_model=args.model,
        )
    else:
        provider = StubModelProvider()

    server = create_local_api(
        SQLiteStore(args.db),
        provider,
        host=args.host,
        port=args.port,
    )
    print(f"ReBounce Stage 1 API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
