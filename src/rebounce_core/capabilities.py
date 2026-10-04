from __future__ import annotations

import html
import ipaddress
import json
import os
import shlex
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .events import Event, EventType
from .permissions import ActionLevel, PermissionPolicy, PermissionRule
from .storage import SQLiteStore


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setting(store: SQLiteStore, companion_id: str, key: str, default: Any = None) -> Any:
    with store._connect() as con:
        row = con.execute(
            "SELECT value FROM companion_settings WHERE companion_id = ? AND key = ?",
            (str(companion_id), key),
        ).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return row["value"]


def _set_setting(store: SQLiteStore, companion_id: str, key: str, value: Any) -> None:
    with store._connect() as con:
        con.execute(
            """
            INSERT INTO companion_settings(companion_id, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(companion_id, key) DO UPDATE SET
              value=excluded.value,
              updated_at=excluded.updated_at
            """,
            (str(companion_id), key, json.dumps(value, ensure_ascii=False), now_iso()),
        )


def _rows(store: SQLiteStore, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with store._connect() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def _row(store: SQLiteStore, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    with store._connect() as con:
        row = con.execute(sql, params).fetchone()
    return dict(row) if row else None


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    enabled: bool = False
    provider: str = "browser"
    language: str = "en-US"
    voice_name: str = ""
    rate: float = 1.0
    pitch: float = 1.0


def get_voice_config(store: SQLiteStore, companion_id: str) -> VoiceConfig:
    raw = _setting(store, companion_id, "voice", {})
    return VoiceConfig(
        enabled=bool(raw.get("enabled", False)),
        provider=str(raw.get("provider", "browser")),
        language=str(raw.get("language", "en-US")),
        voice_name=str(raw.get("voice_name", "")),
        rate=max(0.5, min(2.0, float(raw.get("rate", 1.0)))),
        pitch=max(0.5, min(2.0, float(raw.get("pitch", 1.0)))),
    )


def set_voice_config(store: SQLiteStore, companion_id: str, data: dict[str, Any]) -> VoiceConfig:
    current = get_voice_config(store, companion_id)
    cfg = VoiceConfig(
        enabled=bool(data.get("enabled", current.enabled)),
        provider=str(data.get("provider", current.provider)),
        language=str(data.get("language", current.language)),
        voice_name=str(data.get("voice_name", current.voice_name)),
        rate=max(0.5, min(2.0, float(data.get("rate", current.rate)))),
        pitch=max(0.5, min(2.0, float(data.get("pitch", current.pitch)))),
    )
    _set_setting(store, companion_id, "voice", asdict(cfg))
    return cfg


@dataclass(frozen=True, slots=True)
class PresenceState:
    mode: str = "compact"
    state: str = "idle"
    visible: bool = False
    always_on_top: bool = True


def get_presence(store: SQLiteStore, companion_id: str) -> PresenceState:
    raw = _setting(store, companion_id, "presence", {})
    return PresenceState(
        mode=str(raw.get("mode", "compact")),
        state=str(raw.get("state", "idle")),
        visible=bool(raw.get("visible", False)),
        always_on_top=bool(raw.get("always_on_top", True)),
    )


def set_presence(store: SQLiteStore, companion_id: str, data: dict[str, Any]) -> PresenceState:
    current = get_presence(store, companion_id)
    mode = str(data.get("mode", current.mode))
    state = str(data.get("state", current.state))
    if mode not in {"compact", "pet", "overlay"}:
        raise ValueError("invalid presence mode")
    if state not in {"idle", "listening", "thinking", "speaking", "curious", "working", "away", "error"}:
        raise ValueError("invalid presence state")
    result = PresenceState(
        mode=mode,
        state=state,
        visible=bool(data.get("visible", current.visible)),
        always_on_top=bool(data.get("always_on_top", current.always_on_top)),
    )
    _set_setting(store, companion_id, "presence", asdict(result))
    return result


@dataclass(frozen=True, slots=True)
class AttentionState:
    activity: str = "available"
    quiet_start: str = "22:00"
    quiet_end: str = "08:00"
    proactive_enabled: bool = True
    daily_budget: int = 3


def get_attention(store: SQLiteStore, companion_id: str) -> AttentionState:
    raw = _setting(store, companion_id, "attention", {})
    return AttentionState(
        activity=str(raw.get("activity", "available")),
        quiet_start=str(raw.get("quiet_start", "22:00")),
        quiet_end=str(raw.get("quiet_end", "08:00")),
        proactive_enabled=bool(raw.get("proactive_enabled", True)),
        daily_budget=max(0, int(raw.get("daily_budget", 3))),
    )


def set_attention(store: SQLiteStore, companion_id: str, data: dict[str, Any]) -> AttentionState:
    current = get_attention(store, companion_id)
    activity = str(data.get("activity", current.activity))
    if activity not in {"deep_work", "casual", "available", "voice", "away", "gaming", "meeting", "quiet"}:
        raise ValueError("invalid attention activity")
    state = AttentionState(
        activity=activity,
        quiet_start=str(data.get("quiet_start", current.quiet_start)),
        quiet_end=str(data.get("quiet_end", current.quiet_end)),
        proactive_enabled=bool(data.get("proactive_enabled", current.proactive_enabled)),
        daily_budget=max(0, min(50, int(data.get("daily_budget", current.daily_budget)))),
    )
    _set_setting(store, companion_id, "attention", asdict(state))
    return state


def _in_quiet_hours(now: datetime, start: str, end: str) -> bool:
    try:
        sh, sm = (int(x) for x in start.split(":", 1))
        eh, em = (int(x) for x in end.split(":", 1))
        start_m = sh * 60 + sm
        end_m = eh * 60 + em
        current = now.hour * 60 + now.minute
    except Exception:
        return False
    if start_m == end_m:
        return False
    if start_m < end_m:
        return start_m <= current < end_m
    return current >= start_m or current < end_m


def attention_decision(store: SQLiteStore, companion_id: str) -> str:
    a = get_attention(store, companion_id)
    if not a.proactive_enabled:
        return "do_nothing"
    if a.activity in {"deep_work", "meeting", "gaming", "quiet"}:
        return "save_for_later"
    if _in_quiet_hours(datetime.now().astimezone(), a.quiet_start, a.quiet_end):
        return "save_for_later"
    return "act_now"


class AutonomyManager:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID) -> None:
        self.store = store
        self.user_id = user_id
        self.companion_id = companion_id

    def add_reminder(self, title: str, due_at: str, category: str = "reminder", recurrence: str | None = None) -> dict[str, Any]:
        datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        item = {
            "id": str(uuid4()),
            "companion_id": str(self.companion_id),
            "title": title.strip(),
            "due_at": due_at,
            "category": category,
            "recurrence": recurrence,
            "status": "scheduled",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        if not item["title"]:
            raise ValueError("title must not be empty")
        with self.store._connect() as con:
            con.execute(
                """
                INSERT INTO reminders(id, companion_id, title, due_at, category, recurrence, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(item.values()),
            )
        self.store.save_event(Event(
            type=EventType.REMINDER_CREATED,
            user_id=self.user_id,
            companion_id=self.companion_id,
            data={"reminder_id": item["id"], "title": title},
        ))
        return item

    def list_reminders(self) -> list[dict[str, Any]]:
        return _rows(
            self.store,
            "SELECT * FROM reminders WHERE companion_id = ? ORDER BY due_at ASC",
            (str(self.companion_id),),
        )

    def list_proactive(self) -> list[dict[str, Any]]:
        return _rows(
            self.store,
            """
            SELECT * FROM proactive_queue
            WHERE companion_id = ? AND status IN ('pending', 'deferred')
            ORDER BY created_at DESC
            """,
            (str(self.companion_id),),
        )

    def _daily_count(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        rows = _rows(
            self.store,
            """
            SELECT COUNT(*) AS n FROM proactive_queue
            WHERE companion_id = ? AND created_at >= ? AND status <> 'dismissed'
            """,
            (str(self.companion_id), today),
        )
        return int(rows[0]["n"]) if rows else 0

    def run_due(self) -> list[dict[str, Any]]:
        decision = attention_decision(self.store, str(self.companion_id))
        attention = get_attention(self.store, str(self.companion_id))
        if decision == "do_nothing":
            return []
        if self._daily_count() >= attention.daily_budget:
            return []

        due = _rows(
            self.store,
            """
            SELECT * FROM reminders
            WHERE companion_id = ?
              AND status = 'scheduled'
              AND due_at <= ?
            ORDER BY due_at ASC
            """,
            (str(self.companion_id), now_iso()),
        )
        created: list[dict[str, Any]] = []
        for reminder in due[: max(0, attention.daily_budget - self._daily_count())]:
            status = "pending" if decision == "act_now" else "deferred"
            item = {
                "id": str(uuid4()),
                "companion_id": str(self.companion_id),
                "kind": reminder["category"],
                "title": reminder["title"],
                "body": f"Reminder: {reminder['title']}",
                "status": status,
                "source_ref": f"reminder:{reminder['id']}",
                "created_at": now_iso(),
                "expires_at": None,
            }
            with self.store._connect() as con:
                con.execute(
                    """
                    INSERT INTO proactive_queue(id, companion_id, kind, title, body, status, source_ref, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(item.values()),
                )
                next_status = "completed"
                if reminder["recurrence"]:
                    try:
                        old = datetime.fromisoformat(str(reminder["due_at"]).replace("Z", "+00:00"))
                        next_due = old + timedelta(seconds=_parse_recurrence_seconds(reminder["recurrence"]))
                        con.execute(
                            "UPDATE reminders SET due_at = ?, updated_at = ? WHERE id = ?",
                            (next_due.isoformat(), now_iso(), reminder["id"]),
                        )
                        next_status = "scheduled"
                    except ValueError:
                        pass
                con.execute(
                    "UPDATE reminders SET status = ?, updated_at = ? WHERE id = ?",
                    (next_status, now_iso(), reminder["id"]),
                )
            self.store.save_event(Event(
                type=EventType.REMINDER_TRIGGERED,
                user_id=self.user_id,
                companion_id=self.companion_id,
                data={"reminder_id": reminder["id"], "queue_id": item["id"], "decision": decision},
            ))
            created.append(item)
        return created


def _parse_recurrence_seconds(value: str) -> int:
    parts = value.strip().lower().split()
    if len(parts) != 2:
        raise ValueError("recurrence must look like '1 hour' or '1 day'")
    amount = int(parts[0])
    unit = parts[1].rstrip("s")
    factors = {"minute": 60, "hour": 3600, "day": 86400, "week": 604800}
    if unit not in factors or amount <= 0:
        raise ValueError("unsupported recurrence")
    return amount * factors[unit]


class _SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._href = ""
        self._text: list[str] = []
        self._capture = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if tag == "a" and attrs_d.get("class") == "result__a":
            self._href = attrs_d.get("href") or ""
            self._text = []
            self._capture = True

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture:
            title = html.unescape(" ".join("".join(self._text).split()))
            if title and self._href:
                self.results.append({"title": title[:240], "url": html.unescape(self._href)})
            self._href = ""
            self._text = []
            self._capture = False


class CuriosityEngine:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID) -> None:
        self.store = store
        self.user_id = user_id
        self.companion_id = companion_id

    def _interests(self) -> list[str]:
        memories = _rows(
            self.store,
            """
            SELECT memory_type, content FROM memories
            WHERE companion_id = ? AND status = 'active'
            ORDER BY importance DESC, created_at DESC
            LIMIT 30
            """,
            (str(self.companion_id),),
        )
        terms: list[str] = []
        for row in memories:
            if row["memory_type"] in {"preference", "project", "goal", "fact"}:
                text = str(row["content"]).strip(" .!?")
                if text:
                    terms.append(text)
        return terms[:10]

    def _budget_ok(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        raw = _setting(self.store, str(self.companion_id), "curiosity_budget", {"date": today, "count": 0, "daily_limit": 3, "enabled": False})
        if raw.get("date") != today:
            raw = {"date": today, "count": 0, "daily_limit": raw.get("daily_limit", 3), "enabled": raw.get("enabled", False)}
            _set_setting(self.store, str(self.companion_id), "curiosity_budget", raw)
        return bool(raw.get("enabled", False)) and int(raw.get("count", 0)) < int(raw.get("daily_limit", 3))

    def configure(self, enabled: bool, daily_limit: int = 3) -> dict[str, Any]:
        value = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "count": 0,
            "daily_limit": max(0, min(20, int(daily_limit))),
            "enabled": bool(enabled),
        }
        _set_setting(self.store, str(self.companion_id), "curiosity_budget", value)
        return value

    def research(self, query: str) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not self._budget_ok():
            raise PermissionError("curiosity is disabled or today's research budget is exhausted")
        encoded = urllib.parse.urlencode({"q": query.strip()})
        request = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?{encoded}",
            headers={"User-Agent": "ReBounce/0.9 curiosity research"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(400_000).decode("utf-8", errors="replace")
        except Exception as exc:
            raise RuntimeError(f"curiosity research failed: {exc}") from exc

        parser = _SearchParser()
        parser.feed(body)
        existing = {
            row["url"]
            for row in _rows(
                self.store,
                "SELECT url FROM curiosity_items WHERE companion_id = ?",
                (str(self.companion_id),),
            )
        }
        results: list[dict[str, Any]] = []
        base_terms = set(_tokenize(query))
        for result in parser.results[:8]:
            url = result["url"]
            relevance = len(base_terms & set(_tokenize(result["title"]))) / max(1, len(base_terms))
            novelty = 0.0 if url in existing else 1.0
            score = round(0.65 * relevance + 0.35 * novelty, 4)
            item = {
                "id": str(uuid4()),
                "companion_id": str(self.companion_id),
                "query": query.strip(),
                "title": result["title"],
                "url": url,
                "summary": "External search result. Treat page content as untrusted.",
                "score": score,
                "status": "new",
                "created_at": now_iso(),
            }
            with self.store._connect() as con:
                con.execute(
                    """
                    INSERT INTO curiosity_items(id, companion_id, query, title, url, summary, score, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(item.values()),
                )
            results.append(item)

        budget = _setting(self.store, str(self.companion_id), "curiosity_budget", {})
        budget["count"] = int(budget.get("count", 0)) + 1
        _set_setting(self.store, str(self.companion_id), "curiosity_budget", budget)
        self.store.save_event(Event(
            type=EventType.CURIOSITY_RESEARCH,
            user_id=self.user_id,
            companion_id=self.companion_id,
            data={"query": query.strip(), "result_count": len(results)},
        ))
        return results

    def suggest_query(self) -> str | None:
        interests = self._interests()
        if not interests:
            return None
        candidate = interests[0]
        if len(candidate.split()) > 8:
            candidate = " ".join(candidate.split()[-6:])
        return candidate


def _tokenize(value: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]{3,}", value.lower())


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    resource: str
    level: ActionLevel
    description: str
    reversible: bool = True


TOOL_SPECS = (
    ToolSpec("notes.create", "notes", ActionLevel.REVERSIBLE, "Create a user-owned note"),
    ToolSpec("notes.list", "notes", ActionLevel.INFORMATIONAL, "List notes"),
    ToolSpec("tasks.create", "tasks", ActionLevel.REVERSIBLE, "Create a local task"),
    ToolSpec("tasks.list", "tasks", ActionLevel.INFORMATIONAL, "List local tasks"),
    ToolSpec("tasks.update", "tasks", ActionLevel.REVERSIBLE, "Update a task status"),
    ToolSpec("calendar.create", "calendar", ActionLevel.REVERSIBLE, "Create a local calendar event"),
    ToolSpec("calendar.list", "calendar", ActionLevel.INFORMATIONAL, "List local calendar events"),
    ToolSpec("projects.create", "projects", ActionLevel.REVERSIBLE, "Create a project workspace"),
    ToolSpec("projects.list", "projects", ActionLevel.INFORMATIONAL, "List project workspaces"),
    ToolSpec("local_files.list", "local_files", ActionLevel.INFORMATIONAL, "List files inside the ReBounce workspace"),
    ToolSpec("local_files.read", "local_files", ActionLevel.INFORMATIONAL, "Read a file inside the ReBounce workspace"),
    ToolSpec("local_files.write", "local_files", ActionLevel.APPROVAL_REQUIRED, "Write a file inside the ReBounce workspace"),
    ToolSpec("browser.fetch", "browser", ActionLevel.INFORMATIONAL, "Fetch a public web page without executing page actions"),
    ToolSpec("browser.open", "browser", ActionLevel.INFORMATIONAL, "Open a URL in the user's default browser"),
    ToolSpec("github.get", "github", ActionLevel.INFORMATIONAL, "Read a public GitHub API resource"),
    ToolSpec("mcp.list_tools", "mcp", ActionLevel.INFORMATIONAL, "List tools exposed by an MCP stdio server"),
    ToolSpec("mcp.call", "mcp", ActionLevel.APPROVAL_REQUIRED, "Call an MCP tool after explicit approval"),
)


def load_policy(store: SQLiteStore, companion_id: str) -> PermissionPolicy:
    rules = []
    with store._connect() as con:
        rows = con.execute(
            "SELECT resource, allowed, max_level FROM permissions WHERE companion_id = ?",
            (str(companion_id),),
        ).fetchall()
    if not rows:
        return PermissionPolicy.safe_default()
    for row in rows:
        rules.append(PermissionRule(
            resource=str(row["resource"]),
            max_level=ActionLevel(int(row["max_level"])),
            allowed=bool(row["allowed"]),
        ))
    return PermissionPolicy(tuple(rules))


def set_permission(store: SQLiteStore, companion_id: str, resource: str, allowed: bool, max_level: int) -> dict[str, Any]:
    level = ActionLevel(int(max_level))
    if level == ActionLevel.PROHIBITED:
        allowed = False
    with store._connect() as con:
        con.execute(
            """
            INSERT INTO permissions(companion_id, resource, allowed, max_level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(companion_id, resource) DO UPDATE SET
              allowed=excluded.allowed, max_level=excluded.max_level
            """,
            (str(companion_id), resource, int(bool(allowed)), int(level)),
        )
    return {"resource": resource, "allowed": bool(allowed), "max_level": int(level)}


def _workspace_root(store: SQLiteStore, companion_id: str) -> Path:
    configured = str(_setting(store, companion_id, "filesystem.root", "") or "").strip()
    root = Path(configured).expanduser() if configured else Path.home() / "ReBounce" / "workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_path(root: Path, relative: str) -> Path:
    value = Path(relative)
    if value.is_absolute():
        raise ValueError("path must be relative to the ReBounce workspace")
    target = (root / value).resolve()
    if root != target and root not in target.parents:
        raise PermissionError("path escapes the ReBounce workspace")
    return target


def _ensure_text_size(value: str, limit: int = 1_000_000) -> str:
    if len(value.encode("utf-8")) > limit:
        raise ValueError("content is too large")
    return value


def _public_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only http(s) URLs are allowed")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "0.0.0.0"} or host.endswith(".local"):
        raise PermissionError("local network URLs are not allowed")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RuntimeError(f"unable to resolve host: {host}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise PermissionError("private or local network targets are blocked")
    return parsed


def _mcp_exchange(command: str, args: list[str], method: str, params: dict[str, Any] | None = None) -> Any:
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    payload = json.dumps(request, ensure_ascii=False) + "\n"
    completed = subprocess.run(
        [command, *args],
        input=payload,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"MCP server exited with code {completed.returncode}: {completed.stderr[:500]}")
    for line in completed.stdout.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") == 1:
            if "error" in message:
                raise RuntimeError(json.dumps(message["error"], ensure_ascii=False))
            return message.get("result")
    raise RuntimeError("MCP server returned no matching JSON-RPC response")


class ToolGateway:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID) -> None:
        self.store = store
        self.user_id = user_id
        self.companion_id = companion_id
        self.policy = load_policy(store, str(companion_id))

    def specs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "resource": s.resource,
                "level": int(s.level),
                "description": s.description,
                "reversible": s.reversible,
            }
            for s in TOOL_SPECS
        ]

    def _spec(self, name: str) -> ToolSpec:
        for spec in TOOL_SPECS:
            if spec.name == name:
                return spec
        raise ValueError("unknown tool")

    def _approval(self, tool_name: str, args: dict[str, Any], level: ActionLevel, reason: str) -> dict[str, Any]:
        approval_id = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                """
                INSERT INTO tool_approvals(id, companion_id, tool_name, args_json, requested_level, reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (approval_id, str(self.companion_id), tool_name, json.dumps(args, ensure_ascii=False), int(level), reason, now_iso()),
            )
        self.store.save_event(Event(
            type=EventType.TOOL_APPROVAL_REQUIRED,
            user_id=self.user_id,
            companion_id=self.companion_id,
            data={"approval_id": approval_id, "tool": tool_name, "level": int(level)},
        ))
        return {"status": "approval_required", "approval_id": approval_id, "tool": tool_name, "reason": reason}

    def execute(self, tool_name: str, args: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
        spec = self._spec(tool_name)
        allowed = self.policy.decide(spec.resource, spec.level)
        if not allowed:
            self.store.save_event(Event(
                type=EventType.TOOL_DENIED,
                user_id=self.user_id,
                companion_id=self.companion_id,
                data={"tool": tool_name, "level": int(spec.level)},
            ))
            return {"status": "denied", "tool": tool_name, "reason": "permission policy denied this action"}

        if spec.level >= ActionLevel.APPROVAL_REQUIRED and not approved:
            return self._approval(tool_name, args, spec.level, "This tool can change local or external state.")

        try:
            result = self._run(tool_name, args)
        except Exception as exc:
            self.store.save_event(Event(
                type=EventType.TOOL_EXECUTION_FAILED,
                user_id=self.user_id,
                companion_id=self.companion_id,
                data={"tool": tool_name, "error": str(exc)[:500]},
            ))
            return {"status": "failed", "tool": tool_name, "error": str(exc)}
        self.store.save_event(Event(
            type=EventType.TOOL_EXECUTION,
            user_id=self.user_id,
            companion_id=self.companion_id,
            data={"tool": tool_name, "status": "success"},
        ))
        return {"status": "ok", "tool": tool_name, "result": result}

    def _run(self, tool_name: str, args: dict[str, Any]) -> Any:
        cid = str(self.companion_id)
        if tool_name == "notes.create":
            title = str(args.get("title", "")).strip()
            content = _ensure_text_size(str(args.get("content", "")))
            if not title or not content:
                raise ValueError("title and content are required")
            item = {"id": str(uuid4()), "companion_id": cid, "title": title, "content": content, "tags": str(args.get("tags", "")), "created_at": now_iso(), "updated_at": now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO notes(id, companion_id, title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(item.values()))
            return item
        if tool_name == "notes.list":
            return _rows(self.store, "SELECT * FROM notes WHERE companion_id = ? ORDER BY updated_at DESC LIMIT 100", (cid,))
        if tool_name == "tasks.create":
            title = str(args.get("title", "")).strip()
            if not title:
                raise ValueError("title is required")
            item = {"id": str(uuid4()), "companion_id": cid, "project_id": args.get("project_id"), "title": title, "description": str(args.get("description", "")), "status": "open", "priority": max(1, min(5, int(args.get("priority", 2)))), "due_at": args.get("due_at"), "created_at": now_iso(), "updated_at": now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO tasks(id, companion_id, project_id, title, description, status, priority, due_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(item.values()))
            return item
        if tool_name == "tasks.list":
            return _rows(self.store, "SELECT * FROM tasks WHERE companion_id = ? ORDER BY priority ASC, updated_at DESC LIMIT 100", (cid,))
        if tool_name == "tasks.update":
            task_id = str(args.get("task_id", ""))
            status = str(args.get("status", "open"))
            if status not in {"open", "in_progress", "blocked", "done", "cancelled"}:
                raise ValueError("invalid task status")
            with self.store._connect() as con:
                con.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ? AND companion_id = ?", (status, now_iso(), task_id, cid))
            return _row(self.store, "SELECT * FROM tasks WHERE id = ? AND companion_id = ?", (task_id, cid))
        if tool_name == "calendar.create":
            title = str(args.get("title", "")).strip()
            start_at = str(args.get("start_at", "")).strip()
            if not title or not start_at:
                raise ValueError("title and start_at are required")
            datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            item = {"id": str(uuid4()), "companion_id": cid, "title": title, "start_at": start_at, "end_at": args.get("end_at"), "notes": str(args.get("notes", "")), "status": "scheduled", "created_at": now_iso(), "updated_at": now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO calendar_events(id, companion_id, title, start_at, end_at, notes, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(item.values()))
            return item
        if tool_name == "calendar.list":
            return _rows(self.store, "SELECT * FROM calendar_events WHERE companion_id = ? ORDER BY start_at ASC LIMIT 100", (cid,))
        if tool_name == "projects.create":
            name = str(args.get("name", "")).strip()
            if not name:
                raise ValueError("name is required")
            root = _workspace_root(self.store, cid)
            project_id = str(uuid4())
            path = (root / _slug(name)).resolve()
            path.mkdir(parents=True, exist_ok=True)
            item = {"id": project_id, "companion_id": cid, "name": name, "path": str(path), "description": str(args.get("description", "")), "status": "active", "created_at": now_iso(), "updated_at": now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO projects(id, companion_id, name, path, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", tuple(item.values()))
            return item
        if tool_name == "projects.list":
            return _rows(self.store, "SELECT * FROM projects WHERE companion_id = ? ORDER BY updated_at DESC", (cid,))
        if tool_name.startswith("local_files."):
            root = _workspace_root(self.store, cid)
            relative = str(args.get("path", "."))
            target = _safe_path(root, relative)
            if tool_name == "local_files.list":
                if not target.exists():
                    return []
                if not target.is_dir():
                    raise ValueError("path is not a directory")
                return [{"name": p.name, "type": "directory" if p.is_dir() else "file", "path": str(p.relative_to(root))} for p in sorted(target.iterdir())[:200]]
            if tool_name == "local_files.read":
                if not target.is_file():
                    raise ValueError("file not found")
                return {"path": str(target.relative_to(root)), "content": target.read_text("utf-8")[:1_000_000]}
            if tool_name == "local_files.write":
                content = _ensure_text_size(str(args.get("content", "")))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, "utf-8")
                return {"path": str(target.relative_to(root)), "bytes": len(content.encode("utf-8"))}
        if tool_name == "browser.open":
            parsed = _public_url(str(args.get("url", "")))
            import webbrowser
            webbrowser.open(parsed.geturl())
            return {"url": parsed.geturl(), "opened": True}
        if tool_name == "browser.fetch":
            parsed = _public_url(str(args.get("url", "")))
            req = urllib.request.Request(parsed.geturl(), headers={"User-Agent": "ReBounce/0.9 browser"})
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read(400_000).decode("utf-8", errors="replace")
            return {"url": parsed.geturl(), "content": body, "untrusted": True}
        if tool_name == "github.get":
            path = str(args.get("path", "")).lstrip("/")
            if not path.startswith(("repos/", "users/")):
                raise ValueError("only public GitHub API resource paths are allowed")
            url = "https://api.github.com/" + path
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "ReBounce/0.9"})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read(400_000).decode("utf-8"))
            return {"data": data, "source": url, "untrusted": True}
        if tool_name.startswith("mcp."):
            server_id = str(args.get("server_id", ""))
            server = _row(self.store, "SELECT * FROM mcp_servers WHERE id = ? AND companion_id = ? AND enabled = 1", (server_id, cid))
            if not server:
                raise ValueError("enabled MCP server not found")
            server_args = json.loads(server["args_json"] or "[]")
            if tool_name == "mcp.list_tools":
                return _mcp_exchange(str(server["command"]), list(server_args), "tools/list")
            if tool_name == "mcp.call":
                return _mcp_exchange(str(server["command"]), list(server_args), "tools/call", {
                    "name": str(args.get("name", "")),
                    "arguments": args.get("arguments", {}),
                })
        raise ValueError("unsupported tool")


def _slug(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "project"


def list_approvals(store: SQLiteStore, companion_id: str) -> list[dict[str, Any]]:
    return _rows(
        store,
        "SELECT * FROM tool_approvals WHERE companion_id = ? AND status = 'pending' ORDER BY created_at DESC",
        (str(companion_id),),
    )


def resolve_approval(store: SQLiteStore, approval_id: str, approved: bool) -> dict[str, Any]:
    row = _row(store, "SELECT * FROM tool_approvals WHERE id = ?", (approval_id,))
    if row is None:
        raise ValueError("approval not found")
    status = "approved" if approved else "rejected"
    with store._connect() as con:
        con.execute(
            "UPDATE tool_approvals SET status = ?, resolved_at = ? WHERE id = ?",
            (status, now_iso(), approval_id),
        )
    return {**row, "status": status, "resolved_at": now_iso()}


def compact_journal(store: SQLiteStore, companion_id: str, limit: int = 100) -> list[dict[str, Any]]:
    events = _rows(
        store,
        """
        SELECT id, event_type, data_json, created_at
        FROM events WHERE companion_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (str(companion_id), limit),
    )
    result = []
    for event in events:
        try:
            data = json.loads(event["data_json"] or "{}")
        except Exception:
            data = {}
        result.append({"id": event["id"], "event_type": event["event_type"], "data": data, "created_at": event["created_at"]})
    return result
