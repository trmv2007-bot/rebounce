"""Rendered-dashboard smoke test for Stages 5-9 against the real companion API.

The server is `rebounce_core.api.create_local_api`, so every click exercises the
same route production uses. The companion is created through the dashboard's own
onboarding, and state is then seeded through the public API so views have real
rows to render.
"""

from __future__ import annotations

import json
import re
import tempfile
import threading
from datetime import datetime, timezone
from http.client import HTTPConnection
from pathlib import Path


NAME = "Nova"


class Client:
    def __init__(self, port: int) -> None:
        self.port = port

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        raw = json.dumps(body) if body is not None else None
        connection = HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            connection.request(method, path, body=raw, headers={"Content-Type": "application/json"} if raw else {})
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode() or "{}")
        finally:
            connection.close()

    def expect(self, method: str, path: str, body: dict | None = None) -> dict:
        status, payload = self.request(method, path, body)
        if status >= 400:
            raise AssertionError(f"{method} {path} -> {status} {payload}")
        return payload


def seed(client: Client, cid: str) -> None:
    client.request("PATCH", f"/v1/companions/{cid}/permissions/local_files", {"allowed": True, "max_level": 3})
    client.expect("POST", f"/v1/companions/{cid}/chat", {"content": "hello from smoke"})
    client.expect("POST", f"/v1/companions/{cid}/memories", {"memory_type": "preference", "content": "I prefer concise answers."})
    client.expect("POST", f"/v1/companions/{cid}/milestones", {"title": "Smoke baseline", "description": "Seeded for the UI smoke run"})
    client.expect("POST", f"/v1/companions/{cid}/goals", {"title": "Ship Stage 9"})
    client.expect("POST", f"/v1/companions/{cid}/commitments", {"title": "Review tools"})
    client.expect("POST", f"/v1/companions/{cid}/curiosity", {"enabled": True, "daily_limit": 3})


def main() -> None:
    from playwright.sync_api import sync_playwright

    from rebounce_core.api import create_local_api
    from rebounce_core.provider import StubModelProvider
    from rebounce_core.storage import SQLiteStore

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "workspace"
        sandbox.mkdir()
        store = SQLiteStore(Path(tmp) / "rebounce.db")
        server = create_local_api(store, StubModelProvider(), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = Client(server.server_address[1])

        errors: list[str] = []
        dialogs: list[str] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
            page.on("console", lambda msg: errors.append(f"console: {msg.text}") if msg.type == "error" else None)
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
            base = f"http://127.0.0.1:{client.port}"
            page.goto(f"{base}/", wait_until="networkidle")

            page.get_by_role("button", name="Create companion", exact=True).click()
            page.locator("#onboard-name").fill(NAME)
            page.locator("#onboard-personality").fill("calm")
            page.get_by_role("button", name="Create", exact=True).click()
            page.wait_for_timeout(300)

            cid = page.evaluate("ReBounceBridge.cid()")
            with store._connect() as con:
                con.execute(
                    "INSERT OR REPLACE INTO companion_settings(companion_id,key,value,updated_at) VALUES (?,?,?,?)",
                    (str(cid), "filesystem.root", json.dumps(str(sandbox)), datetime.now(timezone.utc).isoformat()),
                )
            seed(client, cid)
            page.reload(wait_until="networkidle")

            for nav, heading in [
                ("Chat", "Chat that remembers context."),
                ("Memory", f"What {NAME} remembers"),
                ("Relationship", "Shared history"),
                ("Voice", f"Talk with {NAME}"),
                ("Presence", f"Give {NAME} a place on your desktop"),
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
            page.locator("#chat-input").fill("Remember that I prefer concise answers.")
            page.get_by_role("button", name="Send", exact=True).click()
            page.wait_for_timeout(600)
            page.locator("#chat-input").wait_for()
            if page.locator(".bubble").count() < 2:
                raise AssertionError("chat send did not render a user and an assistant bubble")

            page.get_by_role("button", name="Memory", exact=True).click()
            page.locator("[data-edit-memory]").first.wait_for()
            memory_id = page.locator("[data-edit-memory]").first.evaluate("element => element.dataset.editMemory")
            page.get_by_role("button", name="Add memory", exact=True).click()
            page.locator("#mem-content").fill("Smoke memory")
            page.get_by_role("button", name="Save memory", exact=True).click()
            page.locator(f"[data-edit-memory='{memory_id}']").click()
            page.locator("#edit-memory-content").fill("Corrected memory")
            page.locator(f"[data-save-memory='{memory_id}']").click()
            page.locator(f"[data-forget-memory='{memory_id}']").click()
            page.locator("#memory-search").fill("Smoke")
            page.locator("#memory-type").select_option("preference")

            page.get_by_role("button", name="Relationship", exact=True).click()
            for action, title, field in [
                ("Add milestone", "Smoke milestone", "#milestone-title"),
                ("Add goal", "Smoke goal", "#goal-title"),
                ("Add commitment", "Smoke commitment", "#commitment-title"),
            ]:
                page.get_by_role("button", name=action, exact=True).click()
                page.locator(field).fill(title)
                page.get_by_role("button", name=re.sub(r"^Add ", "Save ", action), exact=True).click()
            page.locator("[data-goal-status]").first.click()

            page.get_by_role("button", name="Voice", exact=True).click()
            page.get_by_role("button", name="Start talking", exact=True).click()
            page.evaluate("""const r=window.__lastRecognition; const result={isFinal:true,0:{transcript:'voice smoke'}}; r.onresult({resultIndex:0,results:{0:result,length:1}});""")
            page.wait_for_timeout(600)
            page.get_by_role("button", name="Stop voice", exact=True).click()
            page.locator("#voice-language").select_option("en-IN")
            page.locator("#voice-rate").fill("1.1")
            page.locator("#voice-pitch").fill("0.9")
            page.get_by_role("button", name="Save voice settings", exact=True).click()

            page.get_by_role("button", name="Presence", exact=True).click()
            for mode in ["Compact", "Pet", "Overlay"]:
                page.get_by_role("button", name=mode, exact=True).click()
            page.locator("#presence-visible").check()
            page.locator("#presence-top").check()
            page.get_by_role("button", name="Save presence", exact=True).click()

            page.get_by_role("button", name="Focus", exact=True).click()
            page.locator("#attention-activity").select_option("deep_work")
            page.locator("#quiet-start").fill("21:30")
            page.locator("#quiet-end").fill("08:30")
            page.locator("#proactive-budget").fill("5")
            page.get_by_role("button", name="Save attention", exact=True).click()
            page.get_by_role("button", name="Add reminder", exact=True).click()
            page.locator("#reminder-title").fill("Smoke reminder")
            page.locator("#reminder-due").fill("2026-10-05T10:00")
            page.get_by_role("button", name="Save reminder", exact=True).click()
            page.get_by_role("button", name="Run due jobs", exact=True).click()
            page.wait_for_timeout(400)
            if page.locator("[data-proactive-status]").count():
                page.locator("[data-proactive-status]").first.click()
            if page.locator("[data-reminder-status]").count():
                page.locator("[data-reminder-status]").first.click()

            # Curiosity settings only: "Research now" performs a live web search, which
            # the unit tests cover and a browser test must not depend on.
            page.get_by_role("button", name="Curiosity", exact=True).click()
            page.locator("#curiosity-limit").fill("4")
            page.get_by_role("button", name="Save curiosity settings", exact=True).click()

            page.get_by_role("button", name="Work", exact=True).click()
            for action, fields, save_name in [
                ("New project", [("#project-name", "Smoke project")], "Create project"),
                ("New task", [("#task-title", "Smoke task")], "Create task"),
                ("New note", [("#note-title", "Smoke note"), ("#note-content", "Smoke note body")], "Save note"),
            ]:
                page.get_by_role("button", name=action, exact=True).click()
                for selector, value in fields:
                    page.locator(selector).fill(value)
                page.get_by_role("button", name=save_name, exact=True).click()
            page.get_by_role("button", name="Calendar event", exact=True).click()
            page.locator("#cal-title").fill("Smoke event")
            page.locator("#cal-start").fill("2026-10-05T11:00")
            page.get_by_role("button", name="Save event", exact=True).click()

            page.locator("#tool-name").select_option("notes.create")
            page.locator("#tool-args").fill('{"title":"Tool note","content":"created"}')
            page.get_by_role("button", name="Execute", exact=True).click()
            page.wait_for_timeout(600)

            # Executing a tool re-renders the whole Workbench, so reload before choosing
            # the next one. Without this the picker can be replaced mid-flow and the
            # previous tool runs with empty arguments - which is what CI caught on Linux.
            page.reload(wait_until="networkidle")
            page.get_by_role("button", name="Work", exact=True).click()
            page.get_by_text("Workbench", exact=True).wait_for()

            # An L3 tool has to produce a real approval request, then run exactly once.
            page.locator("#tool-name").select_option("local_files.write")
            page.locator("#tool-args").fill('{"path":"smoke.txt","content":"written by ui smoke"}')
            if page.locator("#tool-name").input_value() != "local_files.write":
                raise AssertionError("the tool picker did not keep the requested tool")
            page.get_by_role("button", name="Execute", exact=True).click()
            page.wait_for_timeout(600)
            outcome = json.loads(page.locator("#tool-output").inner_text())
            if outcome.get("status") != "approval_required":
                raise AssertionError(f"L3 tool did not raise an approval: {outcome}")
            approve = page.locator("[data-approval]").filter(has_text="Approve").first
            approve.wait_for()
            approve.click()
            page.wait_for_timeout(500)
            written = sandbox / "smoke.txt"
            if not written.exists() or written.read_text(encoding="utf-8") != "written by ui smoke":
                raise AssertionError(f"approved tool call did not write {written}")

            permission_buttons = page.locator("button[data-permission]")
            for i in range(permission_buttons.count()):
                permission_buttons.nth(i).click()

            page.get_by_role("button", name="Activity", exact=True).click()
            page.get_by_role("button", name="Refresh", exact=True).click()
            page.get_by_role("button", name="Models", exact=True).click()
            page.get_by_role("button", name="Save provider", exact=True).click()
            page.get_by_role("button", name="Test", exact=True).click()
            page.get_by_role("button", name="Settings", exact=True).click()
            page.locator("#setting-name").fill(f"{NAME} Prime")
            page.get_by_role("button", name="Save identity", exact=True).click()
            page.wait_for_timeout(300)
            with page.expect_download():
                page.get_by_role("button", name="Export my ReBounce data", exact=True).click()

            dashboard = client.expect("GET", f"/v1/companions/{cid}/dashboard")
            if dashboard["companion"]["name"] != f"{NAME} Prime":
                raise AssertionError(f"rename did not persist: {dashboard['companion']}")
            if not any("Smoke" in memory["content"] for memory in dashboard["memories"]):
                raise AssertionError("memory created in the browser was not persisted")
            if not (dashboard["goals"] and dashboard["milestones"] and dashboard["commitments"]):
                raise AssertionError(f"relationship rows missing: {dashboard['relationship']}")

            browser.close()

        server.shutdown()

        if errors:
            raise AssertionError("Browser errors: " + " | ".join(errors))
        print("UI smoke test passed: Stage 5-9 views and workflows exercised against the real API.")


if __name__ == "__main__":
    main()
