from __future__ import annotations

import asyncio
import json
import mimetypes
import os
from argparse import ArgumentParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

from .identity import CompanionIdentity
from .memory import MemoryCandidate
from .models import ModelMessage, ModelRole
from .provider import ModelProvider, OpenAICompatibleProvider, StubModelProvider
from .relationship import RelationshipEngine
from .runtime import CompanionRuntime
from .storage import SQLiteStore

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
MAX_BODY = 1024 * 1024
_PROVIDER = {"provider": "stub", "base_url": "", "model": "", "api_key": None}


def _json(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


class ReBounceHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, store: SQLiteStore, provider: ModelProvider):
        self.store, self.provider = store, provider
        super().__init__(address, ReBounceRequestHandler)


class ReBounceRequestHandler(BaseHTTPRequestHandler):
    server_version = "ReBounce/4.0"

    @property
    def app(self) -> ReBounceHTTPServer:
        return self.server  # type: ignore[return-value]

    def _send(self, status: int | HTTPStatus, body: dict | bytes, content_type: str = "application/json; charset=utf-8") -> None:
        data = _json(body) if isinstance(body, dict) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if size > MAX_BODY:
            raise ValueError("request body is too large")
        raw = self.rfile.read(size)
        value = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _parts(self):
        parsed = urlparse(self.path)
        return parsed, [x for x in parsed.path.split("/") if x]

    def _identity(self, cid: str) -> CompanionIdentity:
        try:
            UUID(cid)
        except ValueError as exc:
            raise ValueError("invalid companion id") from exc
        identity = self.app.store.get_companion(cid)
        if identity is None:
            raise LookupError("companion not found")
        return identity

    def _runtime(self, cid: str) -> CompanionRuntime:
        identity = self._identity(cid)
        return CompanionRuntime(identity, self.app.store, self.app.provider)

    def do_GET(self):
        parsed, parts = self._parts()
        try:
            if parsed.path == "/health":
                return self._send(200, {"status": "ok", "service": "rebounce", "stage": 4})
            if parsed.path in {"/", "/index.html"}:
                return self._static("index.html")
            if len(parts) == 2 and parts[0] == "assets":
                return self._static(parts[1])

            if parsed.path == "/v1/companions":
                user_id = (parse_qs(parsed.query).get("user_id") or [""])[0]
                return self._send(200, {"companions": [self._identity_json(x) for x in self.app.store.list_companions(user_id)]})

            if len(parts) >= 3 and parts[:2] == ["v1", "companions"]:
                identity = self._identity(parts[2])
                cid = str(identity.companion_id)
                if len(parts) == 3:
                    return self._send(200, self._identity_json(identity))
                if len(parts) == 4 and parts[3] == "dashboard":
                    return self._send(200, {
                        "companion": self._identity_json(identity),
                        "conversations": self.app.store.list_conversations(cid),
                        "memories": self.app.store.search_memories(cid, limit=100),
                        "relationship": self.app.store.get_relationship(cid),
                        "milestones": self.app.store.list_milestones(cid, 50),
                        "goals": self.app.store.list_goals(cid),
                        "commitments": self.app.store.list_commitments(cid),
                        "events": self.app.store.list_events(cid, 100),
                        "provider": self._provider_public(),
                    })
                if len(parts) == 5 and parts[3] == "conversations":
                    conversation = self.app.store.get_conversation(parts[4])
                    if not conversation or str(conversation["companion_id"]) != cid:
                        raise LookupError("conversation not found")
                    return self._send(200, {"conversation": conversation, "messages": self.app.store.list_messages(parts[4])})
                if len(parts) == 4 and parts[3] == "memories":
                    return self._send(200, {"memories": self.app.store.search_memories(cid, limit=100)})
                if len(parts) == 4 and parts[3] == "relationship":
                    return self._send(200, {
                        "relationship": self.app.store.get_relationship(cid),
                        "milestones": self.app.store.list_milestones(cid, 100),
                        "goals": self.app.store.list_goals(cid),
                        "commitments": self.app.store.list_commitments(cid),
                    })
                if len(parts) == 4 and parts[3] == "events":
                    return self._send(200, {"events": self.app.store.list_events(cid, 100)})
                if len(parts) == 4 and parts[3] == "export":
                    return self._send(200, self.app.store.export_data(cid))
                if len(parts) == 4 and parts[3] == "conversations":
                    return self._send(200, {"conversations": self.app.store.list_conversations(cid)})

            if parsed.path == "/v1/config/provider":
                return self._send(200, self._provider_public())
            return self._send(404, {"error": "not found"})
        except LookupError as exc:
            return self._send(404, {"error": str(exc)})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except Exception as exc:
            return self._send(500, {"error": str(exc)})

    def do_POST(self):
        parsed, parts = self._parts()
        try:
            data = self._body()
            if parsed.path == "/v1/companions":
                identity = CompanionIdentity(
                    user_id=str(data["user_id"]),
                    name=str(data["name"]),
                    personality=str(data.get("personality", "")),
                )
                self.app.store.save_companion(identity)
                return self._send(201, {"companion_id": str(identity.companion_id), "name": identity.name})

            if len(parts) == 4 and parts[:2] == ["v1", "companions"] and parts[3] == "chat":
                runtime = self._runtime(parts[2])
                content = str(data["content"])
                if bool(data.get("stream")):
                    return self._stream_chat(
                        runtime,
                        content,
                        data.get("conversation_id"),
                        data.get("model"),
                    )
                result = asyncio.run(runtime.handle_user_message(
                    content,
                    conversation_id=data.get("conversation_id"),
                    model=data.get("model"),
                ))
                return self._send(200, {
                    "content": result.content, "provider": result.provider, "model": result.model,
                    "conversation_id": result.conversation_id, "event_id": result.event_id,
                })

            if len(parts) == 4 and parts[:2] == ["v1", "companions"] and parts[3] == "memories":
                identity = self._identity(parts[2])
                candidate = MemoryCandidate(
                    memory_type=str(data.get("memory_type", "fact")),
                    content=str(data["content"]).strip(),
                    key="manual:" + str(uuid4()),
                    confidence=0.99,
                    importance=float(data.get("importance", 0.75)),
                    metadata={"provenance": "user", "manual": True},
                )
                return self._send(201, self._runtime(parts[2]).memory.add(identity, candidate))

            if len(parts) == 4 and parts[:2] == ["v1", "companions"] and parts[3] in {"milestones", "goals", "commitments"}:
                identity = self._identity(parts[2])
                engine = RelationshipEngine(self.app.store)
                if parts[3] == "milestones":
                    item = engine.add_milestone(identity, str(data["title"]), str(data.get("description", "")))
                elif parts[3] == "goals":
                    item = engine.add_goal(identity, str(data["title"]))
                else:
                    item = engine.add_commitment(identity, str(data["title"]), data.get("due_at"))
                return self._send(201, item)

            if parsed.path == "/v1/config/provider":
                global _PROVIDER
                kind = str(data.get("provider", "stub"))
                if kind == "stub":
                    self.app.provider = StubModelProvider()
                    _PROVIDER = {"provider": "stub", "base_url": "", "model": "", "api_key": None}
                else:
                    base_url, model = str(data.get("base_url", "")).rstrip("/"), str(data.get("model", ""))
                    if not base_url or not model:
                        raise ValueError("base_url and model are required")
                    key = data.get("api_key") or None
                    self.app.provider = OpenAICompatibleProvider(base_url, api_key=key, default_model=model)
                    _PROVIDER = {"provider": "openai-compatible", "base_url": base_url, "model": model, "api_key": key}
                return self._send(200, self._provider_public())

            if parsed.path == "/v1/config/provider/test":
                response = asyncio.run(self.app.provider.generate([ModelMessage(ModelRole.USER, "Respond with exactly: ReBounce connected.")]))
                return self._send(200, {"ok": True, "provider": response.provider_name, "model": response.model_name, "content": response.content})
            return self._send(404, {"error": "not found"})
        except (KeyError, TypeError) as exc:
            return self._send(400, {"error": f"missing or invalid field: {exc}"})
        except LookupError as exc:
            return self._send(404, {"error": str(exc)})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except Exception as exc:
            return self._send(502, {"error": str(exc)})

    def _stream_chat(self, runtime, content, conversation_id, model):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        async def emit():
            try:
                async for chunk in runtime.stream_user_message(
                    content,
                    conversation_id=conversation_id,
                    model=model,
                ):
                    payload = {
                        "content": chunk.content,
                        "provider": chunk.provider_name,
                        "model": chunk.model_name,
                        "finish_reason": chunk.finish_reason,
                    }
                    self._write_sse(payload)
                self._write_sse({
                    "done": True,
                    "conversation_id": runtime.state.active_conversation_id,
                    "model": runtime.state.last_model,
                })
            except Exception as exc:
                self._write_sse({"error": str(exc)[:500], "done": True})

        asyncio.run(emit())

    def _write_sse(self, payload):
        data = ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")
        self.wfile.write(data)
        self.wfile.flush()

    def do_PATCH(self):
        parsed, parts = self._parts()
        try:
            data = self._body()
            if len(parts) == 5 and parts[:2] == ["v1", "companions"] and parts[3] == "memories":
                self._identity(parts[2])
                memory = self.app.store.get_memory(parts[4])
                if not memory:
                    raise LookupError("memory not found")
                meta = json.loads(memory["metadata_json"] or "{}")
                meta.setdefault("correction_history", []).append({"at": __import__("datetime").datetime.now().astimezone().isoformat(), "from": memory["content"]})
                self.app.store.update_memory(parts[4], str(data["content"]).strip(), meta, float(memory["confidence"]), float(memory["importance"]))
                return self._send(200, self.app.store.get_memory(parts[4]) or {})
            if len(parts) == 5 and parts[:2] == ["v1", "companions"] and parts[3] == "goals":
                self._identity(parts[2])
                status = str(data.get("status", "active"))
                if status not in {"active", "completed", "paused"}:
                    raise ValueError("invalid goal status")
                self.app.store.update_goal(parts[4], status)
                return self._send(200, {"ok": True})
            if len(parts) == 4 and parts[:2] == ["v1", "companions"] and parts[3] == "settings":
                identity = self._identity(parts[2])
                name, personality = str(data.get("name", identity.name)).strip(), str(data.get("personality", identity.personality))
                self.app.store.update_companion(str(identity.companion_id), name, personality)
                return self._send(200, self._identity_json(self.app.store.get_companion(str(identity.companion_id))))
            return self._send(404, {"error": "not found"})
        except LookupError as exc:
            return self._send(404, {"error": str(exc)})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except Exception as exc:
            return self._send(500, {"error": str(exc)})

    def do_DELETE(self):
        parsed, parts = self._parts()
        try:
            if len(parts) == 5 and parts[:2] == ["v1", "companions"] and parts[3] == "memories":
                self._identity(parts[2])
                self.app.store.delete_memory(parts[4])
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})
        except Exception as exc:
            return self._send(500, {"error": str(exc)})

    def _identity_json(self, identity):
        return {
            "companion_id": str(identity.companion_id), "user_id": identity.user_id,
            "name": identity.name, "personality": identity.personality,
            "relationship_style": identity.relationship_style,
            "created_at": identity.created_at.isoformat(),
        }

    def _provider_public(self):
        return {"provider": _PROVIDER["provider"], "base_url": _PROVIDER["base_url"], "model": _PROVIDER["model"], "configured": self.app.provider.name != "stub"}

    def _static(self, name):
        root = WEB_ROOT.resolve()
        path = (root / name).resolve()
        if root != path.parent and root not in path.parents:
            return self._send(400, {"error": "invalid asset path"})
        if not path.is_file():
            return self._send(404, {"error": "asset not found"})
        data = path.read_bytes()
        self._send(200, data, mimetypes.guess_type(str(path))[0] or "application/octet-stream")

    def log_message(self, *_args):
        pass


def create_local_api(store: SQLiteStore, provider: ModelProvider, *, host="127.0.0.1", port=4100):
    return ReBounceHTTPServer((host, port), store, provider)


def main():
    parser = ArgumentParser(description="Run the ReBounce dashboard and local API")
    parser.add_argument("--db", default=os.getenv("REBOUNCE_DB", "rebounce.db"))
    parser.add_argument("--host", default=os.getenv("REBOUNCE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("REBOUNCE_PORT", "4100")))
    parser.add_argument("--model-url", default=os.getenv("REBOUNCE_MODEL_URL"))
    parser.add_argument("--model", default=os.getenv("REBOUNCE_MODEL"))
    parser.add_argument("--api-key", default=os.getenv("REBOUNCE_MODEL_API_KEY"))
    args = parser.parse_args()

    provider: ModelProvider = StubModelProvider()
    if args.model_url:
        if not args.model:
            parser.error("--model is required with --model-url")
        provider = OpenAICompatibleProvider(args.model_url, api_key=args.api_key, default_model=args.model)
        _PROVIDER.update({"provider": "openai-compatible", "base_url": args.model_url.rstrip("/"), "model": args.model, "api_key": args.api_key})

    server = create_local_api(SQLiteStore(args.db), provider, host=args.host, port=args.port)
    print(f"ReBounce dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
