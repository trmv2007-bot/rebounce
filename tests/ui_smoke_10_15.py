from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1] / "web"
CID = "00000000-0000-0000-0000-000000000101"
CONV = "00000000-0000-0000-0000-000000000102"


def dashboard():
    permissions = [
        {"resource": "screen", "allowed": False, "max_level": 0},
        {"resource": "camera", "allowed": False, "max_level": 0},
        {"resource": "location", "allowed": False, "max_level": 0},
        {"resource": "device_sync", "allowed": True, "max_level": 2},
        {"resource": "delegation", "allowed": True, "max_level": 2},
        {"resource": "avatar", "allowed": True, "max_level": 2},
        {"resource": "shared_activities", "allowed": True, "max_level": 2},
        {"resource": "physical_devices", "allowed": False, "max_level": 0},
        {"resource": "smart_home", "allowed": False, "max_level": 0},
        {"resource": "wearable", "allowed": False, "max_level": 0},
        {"resource": "robotics", "allowed": False, "max_level": 0},
        {"resource": "haptics", "allowed": False, "max_level": 0},
    ]
    return {
        "companion": {"companion_id": CID, "user_id": "ui-test", "name": "Nova", "personality": "calm", "relationship_style": "companion", "created_at": "2026-10-04T00:00:00+00:00"},
        "conversations": [{"id": CONV, "companion_id": CID, "created_at": "2026-10-04T00:00:00+00:00", "updated_at": "2026-10-04T00:00:00+00:00"}],
        "messages": [{"role": "assistant", "content": "Advanced UI smoke test."}],
        "memories": [], "relationship": {"interactions": 0, "active_days": 0, "directness": .5, "warmth": .6, "verbosity": .5, "topics": {}},
        "milestones": [], "goals": [], "commitments": [], "events": [],
        "provider": {"provider": "stub", "base_url": "", "model": "stub", "configured": False},
        "voice": {"enabled": False, "provider": "browser", "language": "en-US", "voice_name": "", "rate": 1, "pitch": 1},
        "presence": {"mode": "compact", "state": "idle", "visible": False, "always_on_top": True},
        "attention": {"activity": "available", "quiet_start": "22:00", "quiet_end": "08:00", "proactive_enabled": True, "daily_budget": 3},
        "reminders": [], "proactive": [], "curiosity": [], "curiosity_budget": {"enabled": False, "daily_limit": 3, "used": 0, "remaining": 3},
        "notes": [], "tasks": [], "calendar": [], "projects": [], "approvals": [], "permissions": permissions, "tools": [],
        "vision": {"active_session": False, "session": None, "context": None, "privacy": {"raw_capture_retained": False, "ephemeral_context": True, "screen_permission": permissions[0], "camera_permission": permissions[1]}},
        "agent": {"plans": [], "jobs": [], "checkpoints": [], "delegations": []},
        "devices": {"devices": [], "offline_queue": [], "recent_sync": []},
        "embodiment": {"profile": None, "room": None, "objects": []},
        "together": {"activities": [], "events": []},
        "physical": {"devices": [], "commands": [], "wearable_context": []},
    }


class Handler(SimpleHTTPRequestHandler):
    state = dashboard()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/assets/"):
            self.path = "/" + path.split("/assets/", 1)[1]
            return super().do_GET()
        if path == "/v1/companions":
            return self._json(200, {"companions": [self.state["companion"]]})
        if path.endswith("/dashboard"):
            return self._json(200, self.state)
        if "/conversations/" in path:
            return self._json(200, {"messages": self.state["messages"]})
        if path == "/v1/config/provider":
            return self._json(200, self.state["provider"])
        return super().do_GET()

    def do_PATCH(self):
        path = urlparse(self.path).path
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        if "/permissions/" in path:
            resource = path.rsplit("/", 1)[-1]
            for item in self.state["permissions"]:
                if item["resource"] == resource:
                    item.update({"allowed": bool(body.get("allowed")), "max_level": int(body.get("max_level", 0))})
                    break
            for key, resource in (("screen_permission", "screen"), ("camera_permission", "camera")):
                if self.state["vision"]["privacy"][key].get("resource") == resource:
                    self.state["vision"]["privacy"][key].update({"allowed": bool(body.get("allowed")), "max_level": int(body.get("max_level", 0))})
            return self._json(200, {"resource": resource, "allowed": bool(body.get("allowed")), "max_level": int(body.get("max_level", 0))})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        if path.endswith("/chat"):
            self.state["messages"].append({"role": "user", "content": body.get("content", "")})
            self.state["messages"].append({"role": "assistant", "content": "Mock reply"})
            return self._json(200, {"content": "Mock reply", "conversation_id": CONV, "provider": "stub", "model": "stub"})
        if path.endswith("/vision"):
            action = body.get("action", "status")
            if action == "start":
                session = {"id": "vs1", "purpose": "intentional screen sharing", "expires_at": "2026-10-04T01:00:00+00:00", "active": True}
                self.state["vision"].update({"active_session": True, "session": session})
                return self._json(200, session)
            if action == "observe":
                self.state["vision"]["context"] = {"observation": body.get("observation", ""), "window_title": body.get("window_title", ""), "app_name": body.get("app_name", ""), "content_hash": "abc"}
                return self._json(200, self.state["vision"]["context"])
            if action == "end":
                self.state["vision"].update({"active_session": False, "session": None})
                return self._json(200, self.state["vision"])
        if path.endswith("/agent"):
            action = body.get("action", "state")
            if action == "create_plan":
                item = {"id": "ap1", "title": body.get("title", ""), "goal": body.get("goal", ""), "status": "pending_approval" if body.get("approval_required", True) else "active"}
                self.state["agent"]["plans"].insert(0, item)
                return self._json(201, item)
            if action == "add_job":
                item = {"id": "aj1", "plan_id": body.get("plan_id"), "title": body.get("title", ""), "step": body.get("step", ""), "status": "queued", "attempts": 0}
                self.state["agent"]["jobs"].insert(0, item)
                return self._json(201, item)
            if action == "approve_plan":
                self.state["agent"]["plans"][0]["status"] = "active"
                return self._json(200, self.state["agent"]["plans"][0])
            if action == "run":
                self.state["agent"]["jobs"][0]["status"] = "checkpointed"
                self.state["agent"]["jobs"][0]["attempts"] = 1
                self.state["agent"]["checkpoints"].insert(0, {"id": "ac1", "job_id": "aj1", "step_index": 0, "note": "resumable"})
                return self._json(200, {"status": "checkpointed"})
            if action == "delegate":
                item = {"id": "ad1", "job_id": body.get("job_id"), "specialist": body.get("specialist", "researcher"), "scope": body.get("scope", ""), "status": "proposed"}
                self.state["agent"]["delegations"].insert(0, item)
                return self._json(201, item)
            if action == "recover":
                return self._json(200, {"recovered": []})
        if path.endswith("/devices"):
            action = body.get("action", "state")
            if action == "register":
                item = {"id": "dv1", "name": body.get("name", ""), "kind": body.get("kind", "desktop"), "platform": body.get("platform", "web"), "status": "online", "capabilities_json": json.dumps(body.get("capabilities", []))}
                self.state["devices"]["devices"].insert(0, item)
                return self._json(201, item)
            if action == "heartbeat":
                self.state["devices"]["devices"][0]["status"] = "online"
                return self._json(200, self.state["devices"]["devices"][0])
            if action == "sync":
                event = {"id": "se1", "sequence": 1, "event_type": body.get("event_type", "state.changed"), "created_at": "2026-10-04T00:00:00+00:00"}
                self.state["devices"]["recent_sync"].insert(0, event)
                return self._json(201, event)
            if action == "pull":
                return self._json(200, {"events": self.state["devices"]["recent_sync"]})
            if action == "offline":
                item = {"id": "oq1", "operation": body.get("operation", "queue"), "status": "queued"}
                self.state["devices"]["offline_queue"].insert(0, item)
                return self._json(201, item)
            if action == "handoff":
                return self._json(200, {"token": "handoff-token"})
        if path.endswith("/embodiment"):
            action = body.get("action", "state")
            if action == "configure":
                self.state["embodiment"]["profile"] = {"profile_name": body.get("profile_name", "ReBounce avatar"), "asset_kind": body.get("asset_kind", "css-orb"), "asset_ref": body.get("asset_ref", ""), "animation_style": body.get("animation_style", "subtle")}
                return self._json(201, self.state["embodiment"]["profile"])
            if action == "room":
                self.state["embodiment"]["room"] = {"name": body.get("name", "Companion Room"), "theme": body.get("theme", "midnight")}
                return self._json(200, self.state["embodiment"]["room"])
            if action == "object":
                item = {"id": "ro1", "kind": body.get("kind", "object"), "name": body.get("name", ""), "state_json": "{}"}
                self.state["embodiment"]["objects"].insert(0, item)
                return self._json(201, item)
        if path.endswith("/together"):
            action = body.get("action", "state")
            if action == "create":
                item = {"id": "ta1", "activity_type": body.get("activity_type", "study"), "title": body.get("title", ""), "status": "active", "started_at": "2026-10-04T00:00:00+00:00"}
                self.state["together"]["activities"].insert(0, item)
                return self._json(201, item)
            if action == "update":
                self.state["together"]["activities"][0]["status"] = body.get("status", "paused")
                return self._json(200, self.state["together"]["activities"][0])
            if action == "event":
                item = {"id": "te1", "activity_id": body.get("activity_id"), "event_type": body.get("event_type", "interaction")}
                self.state["together"]["events"].insert(0, item)
                return self._json(201, item)
        if path.endswith("/physical"):
            action = body.get("action", "state")
            if action == "register":
                item = {"id": "pd1", "name": body.get("name", ""), "kind": body.get("kind", "haptic"), "enabled": 0, "transport": "simulator"}
                self.state["physical"]["devices"].insert(0, item)
                return self._json(201, item)
            if action == "enable":
                self.state["physical"]["devices"][0]["enabled"] = 1
                return self._json(200, self.state["physical"]["devices"][0])
            if action == "command":
                item = {"id": "pc" + str(len(self.state["physical"]["commands"]) + 1), "command": body.get("command", ""), "status": "pending_approval", "requested_level": 3}
                self.state["physical"]["commands"].insert(0, item)
                return self._json(200, item)
            if action == "resolve":
                self.state["physical"]["commands"][0]["status"] = "simulated" if body.get("approved") else "rejected"
                return self._json(200, self.state["physical"]["commands"][0])
        return self._json(404, {"error": "not found"})

    def log_message(self, *_args):
        pass


def main():
    from playwright.sync_api import sync_playwright

    errors = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:" + str(server.server_address[1]) + "/"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda exc: errors.append("pageerror: " + str(exc)))
            page.on("console", lambda msg: errors.append("console: " + msg.text) if msg.type == "error" else None)
            page.goto(url, wait_until="networkidle")
            page.locator('button[data-advanced-view="Vision"]').click()
            page.locator('button[data-advanced-permission="screen"]').click()
            page.locator('button[data-action="vision-start"]').click()
            page.locator("#vision-window").fill("Chrome")
            page.locator("#vision-app").fill("Chrome")
            page.locator("#vision-observation").fill("A project board is visible.")
            page.locator('button[data-action="vision-observe"]').click()
            page.locator('button[data-action="vision-end"]').click()

            page.locator('button[data-advanced-view="Agent"]').click()
            page.locator("#agent-title").fill("Research plan")
            page.locator("#agent-goal").fill("Compare three approved approaches")
            page.locator('button[data-action="agent-create"]').click()
            page.locator("#agent-step-title").fill("Collect sources")
            page.locator("#agent-step").fill("Collect approved source notes")
            page.locator('button[data-action="agent-add-job"]').click()
            page.locator('button[data-action="agent-approve"]').click()
            page.locator('button[data-action="agent-run"]').click()
            page.locator('button[data-action="agent-delegate"]').click()
            page.locator('button[data-action="agent-recover"]').click()

            page.locator('button[data-advanced-view="Devices"]').click()
            page.locator("#device-name").fill("Pixel")
            page.locator("#device-platform").fill("Android")
            page.locator("#device-capabilities").fill("chat,voice,vision")
            page.locator('button[data-action="device-register"]').click()
            page.locator('button[data-action="device-heartbeat"]').click()
            page.locator('button[data-action="device-sync"]').click()
            page.locator('button[data-action="device-pull"]').click()
            page.locator('button[data-action="device-handoff"]').click()

            page.locator('button[data-advanced-view="Avatar"]').click()
            page.locator("#avatar-profile").fill("Nova VRM")
            page.locator("#avatar-ref").fill("avatar.vrm")
            page.locator("#avatar-expressions").fill("calm,joy,focus")
            page.locator('button[data-action="avatar-save"]').click()
            page.locator("#room-name").fill("Research Room")
            page.locator('button[data-action="room-save"]').click()
            page.locator("#room-object-name").fill("Pinned idea")
            page.locator('button[data-action="room-object"]').click()

            page.locator('button[data-advanced-view="Together"]').click()
            page.locator("#together-title").fill("Study session")
            page.locator('button[data-action="together-create"]').click()
            page.locator('button[data-action="together-pause"]').click()
            page.locator('button[data-action="together-event"]').click()
            page.locator('button[data-action="together-complete"]').click()

            page.locator('button[data-advanced-view="Physical"]').click()
            page.locator("#physical-name").fill("Desk light")
            page.locator('button[data-action="physical-register"]').click()
            page.locator('button[data-advanced-permission="physical_devices"]').click()
            page.locator('button[data-advanced-permission="smart_home"]').click()
            page.locator('button[data-action="physical-enable"]').click()
            page.locator("#physical-command").fill("turn-on")
            page.locator('button[data-action="physical-command"]').click()
            page.locator('button[data-physical-resolve][data-approved="false"]').click()
            page.locator("#physical-command").fill("pulse")
            page.locator('button[data-action="physical-command"]').click()
            page.locator('button[data-physical-resolve][data-approved="true"]').click()

            for name in ["Vision", "Agent", "Devices", "Avatar", "Together", "Physical"]:
                page.locator('button[data-advanced-view="' + name + '"]').click()
                assert page.locator("#view").is_visible()
                assert page.locator(".eyebrow").first.is_visible()

            assert not errors, "\n".join(errors)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=2)

    print("UI smoke test passed: all Stage 10-15 views and visible workflows exercised.")


if __name__ == "__main__":
    main()
