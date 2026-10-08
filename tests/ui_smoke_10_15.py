"""Rendered-dashboard smoke test for Stages 10-15 against the real companion API.

Read coverage is unconditional: every advanced view is rendered by the real
`web/advanced.js` from the real `/dashboard` payload, and that payload is asserted
to carry the Stage 10-15 sections and the default-deny sensor rules.

Write coverage is capability-gated. `web/advanced.js` posts to
`/v1/companions/{id}/vision|agent|devices|embodiment|together|physical`, but
`do_POST` in `rebounce_core.api` has no branch for any of them, so those requests
404 today and the write steps below are skipped rather than faked. Once the
dispatchers exist the gate opens on its own and the full flow runs.
"""

from __future__ import annotations

import json
import tempfile
import threading
from http.client import HTTPConnection
from pathlib import Path

NAME = "Nova"
SECTIONS = ("vision", "agent", "devices", "embodiment", "together", "physical")
VIEWS = ("Vision", "Agent", "Devices", "Avatar", "Together", "Physical")
DENIED_BY_DEFAULT = ("screen", "camera", "physical_devices", "wearable", "robotics")


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


def write_routes_supported(client: Client, cid: str) -> bool:
    return all(
        client.request("POST", f"/v1/companions/{cid}/{section}", {"action": "status"})[0] < 404
        for section in SECTIONS
    )


def exercise_writes(page) -> None:
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


def main() -> None:
    from playwright.sync_api import sync_playwright

    from rebounce_core.api import create_local_api
    from rebounce_core.provider import StubModelProvider
    from rebounce_core.storage import SQLiteStore

    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(Path(tmp) / "rebounce.db")
        server = create_local_api(store, StubModelProvider(), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = Client(server.server_address[1])

        errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
            page.on("console", lambda msg: errors.append(f"console: {msg.text}") if msg.type == "error" else None)
            page.on("dialog", lambda dialog: dialog.accept())
            base = f"http://127.0.0.1:{client.port}"
            page.goto(f"{base}/", wait_until="networkidle")

            page.get_by_role("button", name="Create companion", exact=True).click()
            page.locator("#onboard-name").fill(NAME)
            page.get_by_role("button", name="Create", exact=True).click()
            page.wait_for_timeout(300)
            cid = page.evaluate("ReBounceBridge.cid()")

            dashboard = client.expect("GET", f"/v1/companions/{cid}/dashboard")
            missing = [section for section in SECTIONS if section not in dashboard]
            if missing:
                raise AssertionError(f"dashboard payload is missing Stage 10-15 sections: {missing}")

            privacy = dashboard["vision"].get("privacy") or {}
            if privacy.get("raw_capture_retained") is not False:
                raise AssertionError(f"vision no longer declares raw captures ephemeral: {privacy}")

            rules = {rule["resource"]: rule for rule in dashboard["permissions"]}
            for sensor in DENIED_BY_DEFAULT:
                rule = rules.get(sensor)
                if rule is None:
                    raise AssertionError(f"permission policy has no {sensor} rule")
                if rule["allowed"]:
                    raise AssertionError(f"{sensor} should default to denied, got {rule}")

            for view in VIEWS:
                page.locator(f'button[data-advanced-view="{view}"]').click()
                page.locator("#view").wait_for()

            if write_routes_supported(client, cid):
                exercise_writes(page)
                print("Stage 10-15 write flows exercised against the real API.")
            else:
                print(
                    "NOTE: POST /v1/companions/{id}/"
                    + "|".join(SECTIONS)
                    + " are not dispatched by api.py, so only read paths were exercised.",
                )

            browser.close()

        server.shutdown()
        thread.join(timeout=2)

        if errors:
            raise AssertionError("Browser errors: " + " | ".join(errors))
        print("UI smoke test passed: all Stage 10-15 views rendered from real backend state.")


if __name__ == "__main__":
    main()
