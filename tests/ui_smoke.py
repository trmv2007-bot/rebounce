from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1] / "web"
CID = "00000000-0000-0000-0000-000000000001"
CONV = "00000000-0000-0000-0000-000000000002"


def dashboard():
    return {
        "companion": {
            "companion_id": CID, "user_id": "ui-test", "name": "Nova",
            "personality": "calm", "relationship_style": "companion",
            "created_at": "2026-10-04T00:00:00+00:00",
        },
        "conversations": [{"id": CONV, "companion_id": CID, "created_at": "2026-10-04T00:00:00+00:00", "updated_at": "2026-10-04T00:00:00+00:00"}],
        "memories": [{"id": "m1", "memory_type": "preference", "content": "I prefer concise answers.", "confidence": 0.95}],
        "messages": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "Hi from the UI smoke test."}],
        "relationship": {"interactions": 3, "active_days": 2, "directness": .7, "warmth": .8, "verbosity": .6, "topics": {"ReBounce": 3}},
        "milestones": [{"id": "ms1", "title": "Stage 4 shipped", "description": "Dashboard baseline", "created_at": "2026-10-04T00:00:00+00:00"}],
        "goals": [{"id": "g1", "title": "Ship Stage 9", "status": "active"}],
        "commitments": [{"id": "c1", "title": "Review tools", "due_at": None, "status": "open"}],
        "events": [],
        "provider": {"provider": "stub", "base_url": "", "model": "stub", "configured": False},
        "voice": {"enabled": False, "provider": "browser", "language": "en-US", "voice_name": "", "rate": 1, "pitch": 1},
        "presence": {"mode": "compact", "state": "idle", "visible": False, "always_on_top": True},
        "attention": {"activity": "available", "quiet_start": "22:00", "quiet_end": "08:00", "proactive_enabled": True, "daily_budget": 3},
        "reminders": [{"id": "r1", "title": "Existing reminder", "due_at": "2026-10-05T10:00:00+00:00", "status": "scheduled"}],
        "proactive": [{"id": "p1", "title": "Useful discovery", "body": "A queued item for the smoke test.", "status": "pending"}],
        "curiosity": [{"id": "q1", "title": "ReBounce research", "url": "https://example.com/rebounce", "summary": "External search result.", "score": .9}],
        "curiosity_budget": {"enabled": True, "daily_limit": 3, "used": 1, "remaining": 2},
        "notes": [{"id": "n1", "title": "Idea", "content": "Test note", "tags": ""}],
        "tasks": [{"id": "t1", "title": "Test task", "description": "", "status": "open", "priority": 2}],
        "calendar": [{"id": "cal1", "title": "Demo", "start_at": "2026-10-05T10:00:00+00:00", "end_at": None, "notes": ""}],
        "projects": [{"id": "pr1", "name": "Smoke", "path": "/tmp/smoke", "description": "", "status": "active"}],
        "approvals": [{"id": "a1", "tool_name": "local_files.write", "reason": "Test approval", "args_json": json.dumps({"path": "x.txt", "content": "x"})}],
        "permissions": [
            {"resource": "conversation", "allowed": True, "max_level": 1},
            {"resource": "memory", "allowed": True, "max_level": 2},
            {"resource": "local_files", "allowed": False, "max_level": 0},
            {"resource": "browser", "allowed": False, "max_level": 0},
            {"resource": "github", "allowed": False, "max_level": 0},
            {"resource": "mcp", "allowed": False, "max_level": 0},
            {"resource": "notes", "allowed": True, "max_level": 2},
            {"resource": "tasks", "allowed": True, "max_level": 2},
            {"resource": "calendar", "allowed": True, "max_level": 2},
            {"resource": "projects", "allowed": True, "max_level": 2},
            {"resource": "voice", "allowed": True, "max_level": 2},
            {"resource": "presence", "allowed": True, "max_level": 2},
            {"resource": "email", "allowed": False, "max_level": 0},
            {"resource": "payments", "allowed": False, "max_level": 4},
        ],
        "tools": [
            {"name": "notes.create", "resource": "notes", "level": 2, "description": "Create a note", "reversible": True},
            {"name": "tasks.create", "resource": "tasks", "level": 2, "description": "Create a task", "reversible": True},
            {"name": "calendar.create", "resource": "calendar", "level": 2, "description": "Create a calendar event", "reversible": True},
            {"name": "projects.create", "resource": "projects", "level": 2, "description": "Create a project", "reversible": True},
            {"name": "local_files.write", "resource": "local_files", "level": 3, "description": "Write a workspace file", "reversible": True},
        ],
    }


class Handler(SimpleHTTPRequestHandler):
    state = dashboard()
    provider = dict(state["provider"])

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._json(200, {"status": "ok", "stage": 9})
        if path == f"/v1/companions?user_id=":
            return self._json(200, {"companions": [self.state["companion"]]})
        if path.startswith("/v1/companions") and path.endswith("/dashboard"):
            return self._json(200, self.state)
        if path.startswith("/v1/companions") and "/conversations/" in path:
            return self._json(200, {"conversation": self.state["conversations"][0], "messages": self.state["messages"]})
        if path == "/v1/config/provider":
            return self._json(200, self.provider)
        if path.startswith("/v1/companions") and path.endswith("/voice"):
            return self._json(200, self.state["voice"])
        if path.startswith("/v1/companions") and path.endswith("/presence"):
            return self._json(200, self.state["presence"])
        if path.startswith("/v1/companions") and path.endswith("/curiosity"):
            return self._json(200, {"budget": self.state["curiosity_budget"], "items": self.state["curiosity"], "suggested_query": "ReBounce"})
        if path.startswith("/v1/companions") and path.endswith("/tools"):
            return self._json(200, {"tools": self.state["tools"], "approvals": self.state["approvals"]})
        if path.startswith("/v1/companions") and path.endswith("/approvals"):
            return self._json(200, {"approvals": self.state["approvals"]})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        if path.startswith("/v1/companions/") and path.endswith("/chat"):
            return self._json(200, {"content": "Mock companion reply", "provider": "stub", "model": "stub", "conversation_id": CONV, "event_id": "e2"})
        if path == "/v1/config/provider":
            self.provider = {"provider": body.get("provider", "stub"), "base_url": body.get("base_url", ""), "model": body.get("model", "mock"), "configured": body.get("provider") != "stub"}
            self.state["provider"] = self.provider
            return self._json(200, self.provider)
        if path == "/v1/config/provider/test":
            return self._json(200, {"ok": True, "provider": self.provider.get("provider", "stub"), "model": self.provider.get("model", "stub"), "content": "ReBounce connected."})
        if path.endswith("/curiosity"):
            if "query" in body:
                item = {"id": "q2", "title": "Fresh discovery", "url": "https://example.com/fresh", "summary": "New external result.", "score": .8}
                self.state["curiosity"].insert(0, item)
                return self._json(200, {"items": [item], "budget": self.state["curiosity_budget"]})
            self.state["curiosity_budget"].update({"enabled": bool(body.get("enabled")), "daily_limit": int(body.get("daily_limit", 3))})
            return self._json(200, {"budget": self.state["curiosity_budget"], "items": self.state["curiosity"]})
        if path.endswith("/tools"):
            if body.get("tool") == "local_files.write" and not body.get("approved"):
                approval = {"id": "a2", "tool_name": "local_files.write", "reason": "Test approval", "args_json": json.dumps(body.get("args", {}))}
                self.state["approvals"].append(approval)
                return self._json(200, {"status": "approval_required", "approval_id": "a2", "tool": "local_files.write", "reason": "Explicit approval is required."})
            return self._json(200, {"status": "ok", "tool": body.get("tool"), "result": {"mock": True}})
        if "/approvals/" in path:
            aid = path.rsplit("/", 1)[-1]
            self.state["approvals"] = [a for a in self.state["approvals"] if a["id"] != aid]
            return self._json(200, {"status": "approved", "execution": {"status": "ok"}})
        if path.endswith("/reminders"):
            return self._json(201, {"id": "r2", "title": body.get("title", "Reminder"), "due_at": body.get("due_at"), "status": "scheduled"})
        if path.endswith("/autonomy/run"):
            return self._json(200, {"items": [], "decision": "act_now"})
        if path.endswith("/autonomy"):
            self.state["attention"].update(body)
            return self._json(200, self.state["attention"])
        if path.endswith("/voice"):
            self.state["voice"].update(body)
            return self._json(200, self.state["voice"])
        if path.endswith("/presence"):
            self.state["presence"].update(body)
            return self._json(200, self.state["presence"])
        if path.endswith("/milestones") or path.endswith("/goals") or path.endswith("/commitments"):
            return self._json(201, {"id": "new", "title": body.get("title", "New"), "status": "active"})
        if path.endswith("/companions"):
            self.state["companion"].update({"name": body.get("name", "Nova"), "personality": body.get("personality", "")})
            return self._json(201, self.state["companion"])
        return self._json(200, {"ok": True})

    def do_PATCH(self):
        path = urlparse(self.path).path
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        if "/approvals/" in path:
            aid = path.rsplit("/", 1)[-1]
            self.state["approvals"] = [a for a in self.state["approvals"] if a["id"] != aid]
            return self._json(200, {"status": "approved", "execution": {"status": "ok"}})
        if path.endswith("/settings"):
            self.state["companion"].update({"name": body.get("name", "Nova"), "personality": body.get("personality", "")})
            return self._json(200, self.state["companion"])
        if path.endswith("/proactive/p1"):
            return self._json(200, {"ok": True})
        if "/permissions/" in path:
            return self._json(200, {"resource": path.rsplit("/", 1)[-1], "allowed": bool(body.get("allowed")), "max_level": int(body.get("max_level", 0))})
        if "/goals/" in path:
            return self._json(200, {"ok": True})
        if "/reminders/" in path:
            return self._json(200, {"ok": True})
        return self._json(200, {"ok": True})

    def do_DELETE(self):
        return self._json(200, {"ok": True})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.RequestHandlerClass.directory = str(ROOT)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors: list[str] = []
    dialogs: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
        page.add_init_script("""
            class FakeRecognition {
              constructor() { window.__lastRecognition = this; this.lang = ""; this.interimResults = false; this.continuous = false; }
              start() {}
              abort() { this.onend && this.onend(); }
            }
            window.SpeechRecognition = FakeRecognition;
            window.webkitSpeechRecognition = FakeRecognition;
        """)
        page.goto(f"http://127.0.0.1:{server.server_address[1]}/", wait_until="networkidle")

        for nav, heading in [
            ("Chat", "Chat that remembers context."),
            ("Memory", "What Nova remembers"),
            ("Relationship", "Shared history"),
            ("Voice", "Talk with Nova"),
            ("Presence", "Give Nova a place on your desktop"),
            ("Focus", "Attention manager"),
            ("Curiosity", "Curiosity without interruption"),
            ("Work", "Workbench"),
            ("Activity", "What ReBounce has done"),
            ("Models", "Choose the brain"),
            ("Settings", "Companion settings"),
        ]:
            page.get_by_role("button", name=nav, exact=True).click()
            page.get_by_text(heading, exact=True).wait_for()

        page.get_by_role("button", name="Chat", exact=True).click()
        page.locator("#chat-input").fill("hello from smoke")
        page.get_by_role("button", name="Send", exact=True).click()
        page.get_by_text("Mock companion reply", exact=True).wait_for()

        page.get_by_role("button", name="Memory", exact=True).click()
        page.get_by_role("button", name="Add memory", exact=True).click()
        page.locator("#mem-content").fill("Smoke memory")
        page.get_by_role("button", name="Save memory", exact=True).click()
        page.locator("[data-edit-memory='m1']").click()
        page.locator("#edit-memory-content").fill("Corrected memory")
        page.locator("[data-save-memory='m1']").click()
        page.locator("[data-forget-memory='m1']").click()

        page.get_by_role("button", name="Relationship", exact=True).click()
        for action, title, field in [
            ("Add milestone", "Smoke milestone", "#milestone-title"),
            ("Add goal", "Smoke goal", "#goal-title"),
            ("Add commitment", "Smoke commitment", "#commitment-title"),
        ]:
            page.get_by_role("button", name=action, exact=True).click()
            page.locator(field).fill(title)
            page.get_by_role("button", name=re.sub(r"^Add ", "Save ", action), exact=True).click()

        page.get_by_role("button", name="Voice", exact=True).click()
        page.get_by_role("button", name="Start talking", exact=True).click()
        page.evaluate("""const r=window.__lastRecognition; const result={isFinal:true,0:{transcript:'voice smoke'}}; r.onresult({resultIndex:0,results:{0:result,length:1}});""")
        page.get_by_role("button", name="Stop voice", exact=True).click()
        page.get_by_role("button", name="Save voice settings", exact=True).click()

        page.get_by_role("button", name="Presence", exact=True).click()
        for mode in ["Compact", "Pet", "Overlay"]:
            page.get_by_role("button", name=mode, exact=True).click()
        page.locator("#presence-visible").check()
        page.locator("#presence-top").check()
        page.get_by_role("button", name="Save presence", exact=True).click()

        page.get_by_role("button", name="Focus", exact=True).click()
        page.locator("#attention-activity").select_option("deep_work")
        page.get_by_role("button", name="Save attention", exact=True).click()
        page.get_by_role("button", name="Add reminder", exact=True).click()
        page.locator("#reminder-title").fill("Smoke reminder")
        page.locator("#reminder-due").fill("2026-10-05T10:00")
        page.get_by_role("button", name="Save reminder", exact=True).click()
        page.get_by_role("button", name="Run due jobs", exact=True).click()
        page.locator("[data-proactive-status='p1'][data-status='read']").click()
        page.locator("[data-proactive-status='p1'][data-status='dismissed']").click()
        page.locator("[data-reminder-status='r1']").click()

        page.get_by_role("button", name="Curiosity", exact=True).click()
        page.get_by_role("button", name="Save curiosity settings", exact=True).click()
        page.locator("#curiosity-query").fill("ReBounce")
        page.get_by_role("button", name="Research now", exact=True).click()
        page.get_by_text("Fresh discovery", exact=True).wait_for()

        page.get_by_role("button", name="Work", exact=True).click()
        for action, title, fields in [
            ("New project", "Smoke project", [("#project-name", "Smoke project")]),
            ("New task", "Smoke task", [("#task-title", "Smoke task")]),
            ("New note", "Smoke note", [("#note-title", "Smoke note"), ("#note-content", "Smoke note body")]),
        ]:
            page.get_by_role("button", name=action, exact=True).click()
            for selector, value in fields:
                page.locator(selector).fill(value)
            save_name = {"New project":"Create project","New task":"Create task","New note":"Save note"}[action]
            page.get_by_role("button", name=save_name, exact=True).click()
        page.get_by_role("button", name="Calendar event", exact=True).click()
        page.locator("#cal-title").fill("Smoke event")
        page.locator("#cal-start").fill("2026-10-05T11:00")
        page.get_by_role("button", name="Save event", exact=True).click()
        page.locator("#tool-name").select_option("notes.create")
        page.locator("#tool-args").fill('{"title":"Tool note","content":"created"}')
        page.get_by_role("button", name="Execute", exact=True).click()
        page.locator("#tool-output").wait_for()
        page.get_by_role("button", name="Approve", exact=True).click()

        page.get_by_role("button", name="Activity", exact=True).click()
        page.get_by_role("button", name="Refresh", exact=True).click()
        page.get_by_role("button", name="Models", exact=True).click()
        page.get_by_role("button", name="Save provider", exact=True).click()
        page.get_by_role("button", name="Test", exact=True).click()
        page.get_by_role("button", name="Settings", exact=True).click()
        page.locator("#setting-name").fill("Nova Prime")
        page.get_by_role("button", name="Save identity", exact=True).click()
        page.get_by_role("button", name="Settings", exact=True).click()
        with page.expect_download():
            page.get_by_role("button", name="Export my ReBounce data", exact=True).click()

        browser.close()

    server.shutdown()
    if errors:
        raise AssertionError("Browser errors: " + " | ".join(errors))
    print("UI smoke test passed: all Stage 5-9 views and visible workflows exercised.")


if __name__ == "__main__":
    import re
    main()
