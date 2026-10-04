from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import socket
import subprocess
import urllib.parse
import urllib.request
import webbrowser
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


def _get_setting(store: SQLiteStore, cid: str, key: str, default: Any) -> Any:
    with store._connect() as con:
        row = con.execute(
            "SELECT value FROM companion_settings WHERE companion_id = ? AND key = ?",
            (cid, key),
        ).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return default


def _set_setting(store: SQLiteStore, cid: str, key: str, value: Any) -> None:
    with store._connect() as con:
        con.execute(
            """INSERT INTO companion_settings(companion_id,key,value,updated_at)
               VALUES (?,?,?,?)
               ON CONFLICT(companion_id,key) DO UPDATE SET
                 value=excluded.value, updated_at=excluded.updated_at""",
            (cid, key, json.dumps(value, ensure_ascii=False), now_iso()),
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


def get_voice_config(store: SQLiteStore, cid: str) -> VoiceConfig:
    raw = _get_setting(store, cid, "voice", {})
    return VoiceConfig(
        enabled=bool(raw.get("enabled", False)),
        provider=str(raw.get("provider", "browser")),
        language=str(raw.get("language", "en-US")),
        voice_name=str(raw.get("voice_name", "")),
        rate=max(.5, min(2.0, float(raw.get("rate", 1)))),
        pitch=max(.5, min(2.0, float(raw.get("pitch", 1)))),
    )


def set_voice_config(store: SQLiteStore, cid: str, data: dict[str, Any]) -> VoiceConfig:
    cur = get_voice_config(store, cid)
    cfg = VoiceConfig(
        enabled=bool(data.get("enabled", cur.enabled)),
        provider=str(data.get("provider", cur.provider)),
        language=str(data.get("language", cur.language)),
        voice_name=str(data.get("voice_name", cur.voice_name)),
        rate=max(.5, min(2.0, float(data.get("rate", cur.rate)))),
        pitch=max(.5, min(2.0, float(data.get("pitch", cur.pitch)))),
    )
    _set_setting(store, cid, "voice", asdict(cfg))
    return cfg


@dataclass(frozen=True, slots=True)
class PresenceState:
    mode: str = "compact"
    state: str = "idle"
    visible: bool = False
    always_on_top: bool = True


def get_presence(store: SQLiteStore, cid: str) -> PresenceState:
    raw = _get_setting(store, cid, "presence", {})
    return PresenceState(
        mode=str(raw.get("mode", "compact")),
        state=str(raw.get("state", "idle")),
        visible=bool(raw.get("visible", False)),
        always_on_top=bool(raw.get("always_on_top", True)),
    )


def set_presence(store: SQLiteStore, cid: str, data: dict[str, Any]) -> PresenceState:
    cur = get_presence(store, cid)
    mode = str(data.get("mode", cur.mode))
    state = str(data.get("state", cur.state))
    if mode not in {"compact", "pet", "overlay"}:
        raise ValueError("invalid presence mode")
    if state not in {"idle","listening","thinking","speaking","curious","working","away","error"}:
        raise ValueError("invalid presence state")
    out = PresenceState(mode, state, bool(data.get("visible", cur.visible)), bool(data.get("always_on_top", cur.always_on_top)))
    _set_setting(store, cid, "presence", asdict(out))
    return out


@dataclass(frozen=True, slots=True)
class AttentionState:
    activity: str = "available"
    quiet_start: str = "22:00"
    quiet_end: str = "08:00"
    proactive_enabled: bool = True
    daily_budget: int = 3


def get_attention(store: SQLiteStore, cid: str) -> AttentionState:
    raw = _get_setting(store, cid, "attention", {})
    return AttentionState(
        str(raw.get("activity", "available")),
        str(raw.get("quiet_start", "22:00")),
        str(raw.get("quiet_end", "08:00")),
        bool(raw.get("proactive_enabled", True)),
        max(0, min(50, int(raw.get("daily_budget", 3)))),
    )


def set_attention(store: SQLiteStore, cid: str, data: dict[str, Any]) -> AttentionState:
    cur = get_attention(store, cid)
    activity = str(data.get("activity", cur.activity))
    if activity not in {"deep_work","casual","available","voice","away","gaming","meeting","quiet"}:
        raise ValueError("invalid attention activity")
    out = AttentionState(
        activity,
        str(data.get("quiet_start", cur.quiet_start)),
        str(data.get("quiet_end", cur.quiet_end)),
        bool(data.get("proactive_enabled", cur.proactive_enabled)),
        max(0, min(50, int(data.get("daily_budget", cur.daily_budget)))),
    )
    _set_setting(store, cid, "attention", asdict(out))
    return out


def _in_quiet_hours(now: datetime, start: str, end: str) -> bool:
    try:
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        s, e, c = sh*60+sm, eh*60+em, now.hour*60+now.minute
    except Exception:
        return False
    return (s <= c < e) if s < e else (c >= s or c < e)


def attention_decision(store: SQLiteStore, cid: str) -> str:
    a = get_attention(store, cid)
    if not a.proactive_enabled:
        return "do_nothing"
    if a.activity in {"deep_work","meeting","gaming","quiet"} or _in_quiet_hours(datetime.now().astimezone(), a.quiet_start, a.quiet_end):
        return "save_for_later"
    return "act_now"


class AutonomyManager:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID) -> None:
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def add_reminder(self, title: str, due_at: str, category: str = "reminder", recurrence: str | None = None) -> dict[str, Any]:
        title = title.strip()
        if not title:
            raise ValueError("title must not be empty")
        datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        item = {
            "id": str(uuid4()), "companion_id": str(self.companion_id), "title": title,
            "due_at": due_at, "category": category, "recurrence": recurrence,
            "status": "scheduled", "created_at": now_iso(), "updated_at": now_iso(),
        }
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO reminders(id,companion_id,title,due_at,category,recurrence,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                tuple(item.values()),
            )
        self.store.save_event(Event(EventType.REMINDER_CREATED, self.user_id, self.companion_id, {"reminder_id": item["id"], "title": title}))
        return item

    def list_reminders(self) -> list[dict[str, Any]]:
        return _rows(self.store, "SELECT * FROM reminders WHERE companion_id=? ORDER BY due_at ASC", (str(self.companion_id),))

    def list_proactive(self) -> list[dict[str, Any]]:
        return _rows(self.store, "SELECT * FROM proactive_queue WHERE companion_id=? AND status IN ('pending','deferred') ORDER BY created_at DESC", (str(self.companion_id),))

    def run_due(self) -> list[dict[str, Any]]:
        decision = attention_decision(self.store, str(self.companion_id))
        if decision == "do_nothing":
            return []
        attention = get_attention(self.store, str(self.companion_id))
        today = datetime.now(timezone.utc).date().isoformat()
        daily = _rows(self.store, "SELECT COUNT(*) AS n FROM proactive_queue WHERE companion_id=? AND created_at>=? AND status<>'dismissed'", (str(self.companion_id), today))
        used = int(daily[0]["n"]) if daily else 0
        if used >= attention.daily_budget:
            return []
        due = _rows(self.store, """SELECT * FROM reminders WHERE companion_id=? AND status='scheduled' AND due_at<=? ORDER BY due_at ASC""", (str(self.companion_id), now_iso()))
        out = []
        for reminder in due[:max(0, attention.daily_budget - used)]:
            item = {
                "id": str(uuid4()), "companion_id": str(self.companion_id),
                "kind": reminder["category"], "title": reminder["title"],
                "body": f"Reminder: {reminder['title']}",
                "status": "pending" if decision == "act_now" else "deferred",
                "source_ref": f"reminder:{reminder['id']}", "created_at": now_iso(), "expires_at": None,
            }
            with self.store._connect() as con:
                con.execute("INSERT INTO proactive_queue(id,companion_id,kind,title,body,status,source_ref,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)", tuple(item.values()))
                next_status = "completed"
                if reminder["recurrence"]:
                    try:
                        old = datetime.fromisoformat(reminder["due_at"].replace("Z","+00:00"))
                        next_due = old + _recurrence_delta(str(reminder["recurrence"]))
                        con.execute("UPDATE reminders SET due_at=?,updated_at=? WHERE id=?", (next_due.isoformat(), now_iso(), reminder["id"]))
                        next_status = "scheduled"
                    except ValueError:
                        pass
                con.execute("UPDATE reminders SET status=?,updated_at=? WHERE id=?", (next_status, now_iso(), reminder["id"]))
            self.store.save_event(Event(EventType.REMINDER_TRIGGERED, self.user_id, self.companion_id, {"reminder_id": reminder["id"], "queue_id": item["id"], "decision": decision}))
            out.append(item)
        return out


def _recurrence_delta(value: str) -> timedelta:
    m = re.fullmatch(r"\s*(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)\s*", value.lower())
    if not m:
        raise ValueError("unsupported recurrence")
    amount = int(m.group(1))
    return timedelta(**{m.group(2).rstrip("s"): amount})


class _SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str,str]] = []
        self.href = ""
        self.text: list[str] = []
        self.active = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str,str|None]]) -> None:
        attrs = dict(attrs)
        if tag == "a" and attrs.get("class") == "result__a":
            self.href, self.text, self.active = attrs.get("href") or "", [], True

    def handle_data(self, data: str) -> None:
        if self.active:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.active:
            title = html.unescape(" ".join("".join(self.text).split()))
            if title and self.href:
                self.results.append({"title": title[:240], "url": html.unescape(self.href)})
            self.href, self.text, self.active = "", [], False


class CuriosityEngine:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID) -> None:
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def configure(self, enabled: bool, daily_limit: int = 3) -> dict[str,Any]:
        raw = {"date": datetime.now(timezone.utc).date().isoformat(), "count": 0, "daily_limit": max(0,min(20,int(daily_limit))), "enabled": bool(enabled)}
        _set_setting(self.store, str(self.companion_id), "curiosity_budget", raw)
        return raw

    def budget(self) -> dict[str,Any]:
        today = datetime.now(timezone.utc).date().isoformat()
        raw = _get_setting(self.store, str(self.companion_id), "curiosity_budget", {"date":today,"count":0,"daily_limit":3,"enabled":False})
        if raw.get("date") != today:
            raw = {**raw, "date": today, "count": 0}
            _set_setting(self.store, str(self.companion_id), "curiosity_budget", raw)
        return {"enabled":bool(raw.get("enabled",False)),"daily_limit":int(raw.get("daily_limit",3)),"used":int(raw.get("count",0)),"remaining":max(0,int(raw.get("daily_limit",3))-int(raw.get("count",0)))}

    def _interests(self) -> list[str]:
        return [str(r["content"]) for r in _rows(self.store, """SELECT content FROM memories WHERE companion_id=? AND status='active' AND memory_type IN ('preference','project','goal','fact') ORDER BY importance DESC,created_at DESC LIMIT 20""", (str(self.companion_id),)) if str(r["content"]).strip()]

    def suggest_query(self) -> str | None:
        interests = self._interests()
        if not interests:
            return None
        value = interests[0].strip(" .!?")
        return " ".join(value.split()[-8:])

    def list_items(self) -> list[dict[str,Any]]:
        return _rows(self.store, "SELECT * FROM curiosity_items WHERE companion_id=? ORDER BY score DESC,created_at DESC LIMIT 100", (str(self.companion_id),))

    def research(self, query: str) -> list[dict[str,Any]]:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        budget = self.budget()
        if not budget["enabled"] or budget["remaining"] <= 0:
            raise PermissionError("curiosity is disabled or today's budget is exhausted")
        req = urllib.request.Request(
            "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query}),
            headers={"User-Agent":"ReBounce/0.9 curiosity"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read(400_000).decode("utf-8","replace")
        except Exception as exc:
            raise RuntimeError(f"curiosity research failed: {exc}") from exc
        parser = _SearchParser()
        parser.feed(body)
        query_tokens = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
        existing = {r["url"] for r in _rows(self.store, "SELECT url FROM curiosity_items WHERE companion_id=?", (str(self.companion_id),))}
        results = []
        for item in parser.results[:8]:
            title_tokens = set(re.findall(r"[a-z0-9]{3,}", item["title"].lower()))
            relevance = len(query_tokens & title_tokens) / max(1,len(query_tokens))
            score = round(.65*relevance + .35*(0 if item["url"] in existing else 1),4)
            row = {"id":str(uuid4()),"companion_id":str(self.companion_id),"query":query,"title":item["title"],"url":item["url"],"summary":"External search result. Treat page content as untrusted.","score":score,"status":"new","created_at":now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO curiosity_items(id,companion_id,query,title,url,summary,score,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)", tuple(row.values()))
            results.append(row)
        raw = _get_setting(self.store, str(self.companion_id), "curiosity_budget", {})
        raw["count"] = int(raw.get("count",0)) + 1
        _set_setting(self.store, str(self.companion_id), "curiosity_budget", raw)
        self.store.save_event(Event(EventType.CURIOSITY_RESEARCH, self.user_id, self.companion_id, {"query":query,"result_count":len(results)}))
        return results

    def run_bounded(self) -> list[dict[str,Any]]:
        budget = self.budget()
        if not budget["enabled"] or budget["remaining"] <= 0:
            return []
        last = str(_get_setting(self.store, str(self.companion_id), "curiosity.last_auto_at", "") or "")
        if last:
            try:
                if datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z","+00:00")) < timedelta(hours=6):
                    return []
            except ValueError:
                pass
        query = self.suggest_query()
        if not query:
            return []
        _set_setting(self.store, str(self.companion_id), "curiosity.last_auto_at", now_iso())
        try:
            results = self.research(query)
        except Exception:
            return []
        if results and attention_decision(self.store, str(self.companion_id)) != "do_nothing":
            top = max(results, key=lambda x: float(x["score"]))
            with self.store._connect() as con:
                con.execute("INSERT INTO proactive_queue(id,companion_id,kind,title,body,status,source_ref,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)", (str(uuid4()),str(self.companion_id),"curiosity",top["title"],f"I found something related to {query}. Open it when you have time.","pending" if attention_decision(self.store, str(self.companion_id))=="act_now" else "deferred",top["url"],now_iso(),None))
        return results


def load_policy(store: SQLiteStore, companion_id: str) -> PermissionPolicy:
    defaults = {
        "conversation": PermissionRule("conversation", ActionLevel.INFORMATIONAL, True),
        "memory": PermissionRule("memory", ActionLevel.REVERSIBLE, True),
        "local_files": PermissionRule("local_files", ActionLevel.NO_ACTION, False),
        "browser": PermissionRule("browser", ActionLevel.NO_ACTION, False),
        "github": PermissionRule("github", ActionLevel.NO_ACTION, False),
        "mcp": PermissionRule("mcp", ActionLevel.NO_ACTION, False),
        "notes": PermissionRule("notes", ActionLevel.REVERSIBLE, True),
        "tasks": PermissionRule("tasks", ActionLevel.REVERSIBLE, True),
        "calendar": PermissionRule("calendar", ActionLevel.REVERSIBLE, True),
        "projects": PermissionRule("projects", ActionLevel.REVERSIBLE, True),
        "voice": PermissionRule("voice", ActionLevel.REVERSIBLE, True),
        "presence": PermissionRule("presence", ActionLevel.REVERSIBLE, True),
        "email": PermissionRule("email", ActionLevel.NO_ACTION, False),
        "payments": PermissionRule("payments", ActionLevel.PROHIBITED, False),
    }
    with store._connect() as con:
        for row in con.execute("SELECT resource,allowed,max_level FROM permissions WHERE companion_id=?", (str(companion_id),)).fetchall():
            defaults[row["resource"]] = PermissionRule(row["resource"], ActionLevel(int(row["max_level"])), bool(row["allowed"]))
    return PermissionPolicy(tuple(defaults.values()))


def set_permission(store: SQLiteStore, companion_id: str, resource: str, allowed: bool, max_level: int) -> dict[str,Any]:
    level = ActionLevel(int(max_level))
    if level == ActionLevel.PROHIBITED:
        allowed = False
    with store._connect() as con:
        con.execute(
            """INSERT INTO permissions(companion_id,resource,allowed,max_level) VALUES (?,?,?,?)
               ON CONFLICT(companion_id,resource) DO UPDATE SET allowed=excluded.allowed,max_level=excluded.max_level""",
            (str(companion_id),resource,int(bool(allowed)),int(level)),
        )
    return {"resource":resource,"allowed":bool(allowed),"max_level":int(level)}


def _root(store: SQLiteStore, cid: str) -> Path:
    value = str(_get_setting(store, cid, "filesystem.root", "") or "").strip()
    root = Path(value).expanduser() if value else Path.home() / "ReBounce" / "workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_path(root: Path, relative: str) -> Path:
    p = Path(relative)
    if p.is_absolute():
        raise PermissionError("path must be relative")
    target = (root / p).resolve()
    if target != root and root not in target.parents:
        raise PermissionError("path escapes workspace")
    return target


def _public_url(url: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme not in {"http","https"} or not p.hostname:
        raise ValueError("only http(s) URLs are allowed")
    if p.hostname.lower() in {"localhost","127.0.0.1","0.0.0.0"} or p.hostname.lower().endswith(".local"):
        raise PermissionError("local targets are blocked")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme=="https" else 80), type=socket.SOCK_STREAM)
        if any(ipaddress.ip_address(i[4][0]).is_private or ipaddress.ip_address(i[4][0]).is_loopback for i in infos):
            raise PermissionError("private network targets are blocked")
    except socket.gaierror as exc:
        raise RuntimeError(f"host resolution failed: {p.hostname}") from exc
    return p.geturl()


def _mcp_exchange(command: str, args: list[str], method: str, params: dict[str,Any] | None = None) -> Any:
    request = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or {}}, ensure_ascii=False) + "\n"
    proc = subprocess.run([command,*args], input=request, text=True, capture_output=True, timeout=20, check=False)
    if proc.returncode:
        raise RuntimeError(f"MCP server exited with code {proc.returncode}: {proc.stderr[:300]}")
    for line in proc.stdout.splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == 1:
            if "error" in msg:
                raise RuntimeError(json.dumps(msg["error"], ensure_ascii=False))
            return msg.get("result")
    raise RuntimeError("MCP server returned no matching response")


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    resource: str
    level: ActionLevel
    description: str
    reversible: bool = True


TOOL_SPECS = (
    ToolSpec("notes.create","notes",ActionLevel.REVERSIBLE,"Create a local note"),
    ToolSpec("notes.list","notes",ActionLevel.INFORMATIONAL,"List local notes"),
    ToolSpec("tasks.create","tasks",ActionLevel.REVERSIBLE,"Create a local task"),
    ToolSpec("tasks.list","tasks",ActionLevel.INFORMATIONAL,"List local tasks"),
    ToolSpec("tasks.update","tasks",ActionLevel.REVERSIBLE,"Update a task"),
    ToolSpec("calendar.create","calendar",ActionLevel.REVERSIBLE,"Create a local calendar event"),
    ToolSpec("calendar.list","calendar",ActionLevel.INFORMATIONAL,"List local calendar events"),
    ToolSpec("projects.create","projects",ActionLevel.REVERSIBLE,"Create a project workspace"),
    ToolSpec("projects.list","projects",ActionLevel.INFORMATIONAL,"List project workspaces"),
    ToolSpec("local_files.list","local_files",ActionLevel.INFORMATIONAL,"List workspace files"),
    ToolSpec("local_files.read","local_files",ActionLevel.INFORMATIONAL,"Read a workspace file"),
    ToolSpec("local_files.write","local_files",ActionLevel.APPROVAL_REQUIRED,"Write a workspace file"),
    ToolSpec("browser.fetch","browser",ActionLevel.INFORMATIONAL,"Fetch a public web page as untrusted content"),
    ToolSpec("browser.open","browser",ActionLevel.INFORMATIONAL,"Open a public URL in the default browser"),
    ToolSpec("github.get","github",ActionLevel.INFORMATIONAL,"Read a public GitHub API resource"),
    ToolSpec("mcp.list_tools","mcp",ActionLevel.INFORMATIONAL,"List tools from an MCP server"),
    ToolSpec("mcp.call","mcp",ActionLevel.APPROVAL_REQUIRED,"Call an MCP tool after approval"),
)


class ToolGateway:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID) -> None:
        self.store, self.user_id, self.companion_id = store, user_id, companion_id
        self.policy = load_policy(store, str(companion_id))

    def specs(self) -> list[dict[str,Any]]:
        return [{"name":s.name,"resource":s.resource,"level":int(s.level),"description":s.description,"reversible":s.reversible} for s in TOOL_SPECS]

    def _spec(self, name: str) -> ToolSpec:
        for spec in TOOL_SPECS:
            if spec.name == name:
                return spec
        raise ValueError("unknown tool")

    def _needs_approval(self, tool: ToolSpec, approved: bool) -> bool:
        return tool.level >= ActionLevel.APPROVAL_REQUIRED and not approved

    def _queue_approval(self, tool: ToolSpec, args: dict[str,Any]) -> dict[str,Any]:
        approval_id = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO tool_approvals(id,companion_id,tool_name,args_json,requested_level,reason,status,created_at) VALUES (?,?,?,?,?,?,'pending',?)",
                (approval_id,str(self.companion_id),tool.name,json.dumps(args,ensure_ascii=False),int(tool.level),"This action can change local or external state.",now_iso()),
            )
        self.store.save_event(Event(EventType.TOOL_APPROVAL_REQUIRED,self.user_id,self.companion_id,{"approval_id":approval_id,"tool":tool.name,"level":int(tool.level)}))
        return {"status":"approval_required","approval_id":approval_id,"tool":tool.name,"reason":"Explicit approval is required before this change."}

    def execute(self, tool_name: str, args: dict[str,Any], *, approved: bool=False) -> dict[str,Any]:
        spec = self._spec(tool_name)
        if not self.policy.decide(spec.resource, spec.level):
            self.store.save_event(Event(EventType.TOOL_DENIED,self.user_id,self.companion_id,{"tool":tool_name,"level":int(spec.level)}))
            return {"status":"denied","tool":tool_name,"reason":"Permission policy denied this action."}
        if self._needs_approval(spec, approved):
            return self._queue_approval(spec,args)
        try:
            result = self._run(spec.name,args)
        except Exception as exc:
            self.store.save_event(Event(EventType.TOOL_EXECUTION_FAILED,self.user_id,self.companion_id,{"tool":tool_name,"error":str(exc)[:500]}))
            return {"status":"failed","tool":tool_name,"error":str(exc)}
        self.store.save_event(Event(EventType.TOOL_EXECUTION,self.user_id,self.companion_id,{"tool":tool_name,"status":"success"}))
        return {"status":"ok","tool":tool_name,"result":result}

    def _run(self, name: str, args: dict[str,Any]) -> Any:
        cid = str(self.companion_id)
        if name == "notes.create":
            title, content = str(args.get("title","")).strip(), str(args.get("content",""))
            if not title or not content:
                raise ValueError("title and content are required")
            item={"id":str(uuid4()),"companion_id":cid,"title":title,"content":content[:1_000_000],"tags":str(args.get("tags","")),"created_at":now_iso(),"updated_at":now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO notes(id,companion_id,title,content,tags,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", tuple(item.values()))
            return item
        if name == "notes.list":
            return _rows(self.store,"SELECT * FROM notes WHERE companion_id=? ORDER BY updated_at DESC LIMIT 100",(cid,))
        if name == "tasks.create":
            title=str(args.get("title","")).strip()
            if not title: raise ValueError("title is required")
            item={"id":str(uuid4()),"companion_id":cid,"project_id":args.get("project_id"),"title":title,"description":str(args.get("description","")),"status":"open","priority":max(1,min(5,int(args.get("priority",2)))),"due_at":args.get("due_at"),"created_at":now_iso(),"updated_at":now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO tasks(id,companion_id,project_id,title,description,status,priority,due_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(item.values()))
            return item
        if name == "tasks.list":
            return _rows(self.store,"SELECT * FROM tasks WHERE companion_id=? ORDER BY priority ASC,updated_at DESC LIMIT 100",(cid,))
        if name == "tasks.update":
            tid,status=str(args.get("task_id","")),str(args.get("status","open"))
            if status not in {"open","in_progress","blocked","done","cancelled"}: raise ValueError("invalid task status")
            with self.store._connect() as con:
                con.execute("UPDATE tasks SET status=?,updated_at=? WHERE id=? AND companion_id=?",(status,now_iso(),tid,cid))
            return _row(self.store,"SELECT * FROM tasks WHERE id=? AND companion_id=?",(tid,cid))
        if name == "calendar.create":
            title,start=str(args.get("title","")).strip(),str(args.get("start_at","")).strip()
            if not title or not start: raise ValueError("title and start_at are required")
            datetime.fromisoformat(start.replace("Z","+00:00"))
            item={"id":str(uuid4()),"companion_id":cid,"title":title,"start_at":start,"end_at":args.get("end_at"),"notes":str(args.get("notes","")),"status":"scheduled","created_at":now_iso(),"updated_at":now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO calendar_events(id,companion_id,title,start_at,end_at,notes,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", tuple(item.values()))
            return item
        if name == "calendar.list":
            return _rows(self.store,"SELECT * FROM calendar_events WHERE companion_id=? ORDER BY start_at ASC LIMIT 100",(cid,))
        if name == "projects.create":
            title=str(args.get("name","")).strip()
            if not title: raise ValueError("name is required")
            root=_root(self.store,cid); pid=str(uuid4()); path=(root/_slug(title)).resolve(); path.mkdir(parents=True,exist_ok=True)
            item={"id":pid,"companion_id":cid,"name":title,"path":str(path),"description":str(args.get("description","")),"status":"active","created_at":now_iso(),"updated_at":now_iso()}
            with self.store._connect() as con:
                con.execute("INSERT INTO projects(id,companion_id,name,path,description,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", tuple(item.values()))
            return item
        if name == "projects.list":
            return _rows(self.store,"SELECT * FROM projects WHERE companion_id=? ORDER BY updated_at DESC",(cid,))
        if name.startswith("local_files."):
            target=_safe_path(_root(self.store,cid),str(args.get("path",".")))
            if name=="local_files.list":
                if not target.exists(): return []
                if not target.is_dir(): raise ValueError("path is not a directory")
                return [{"name":p.name,"type":"directory" if p.is_dir() else "file","path":str(p.relative_to(_root(self.store,cid)))} for p in sorted(target.iterdir())[:200]]
            if name=="local_files.read":
                if not target.is_file(): raise ValueError("file not found")
                return {"path":str(target.relative_to(_root(self.store,cid))),"content":target.read_text("utf-8")[:1_000_000]}
            if name=="local_files.write":
                body=str(args.get("content",""))
                target.parent.mkdir(parents=True,exist_ok=True); target.write_text(body[:1_000_000],"utf-8")
                return {"path":str(target.relative_to(_root(self.store,cid))),"bytes":len(body.encode("utf-8"))}
        if name == "browser.open":
            url=_public_url(str(args.get("url",""))); webbrowser.open(url); return {"url":url,"opened":True}
        if name == "browser.fetch":
            url=_public_url(str(args.get("url",""))); req=urllib.request.Request(url,headers={"User-Agent":"ReBounce/0.9 browser"})
            with urllib.request.urlopen(req,timeout=15) as response: body=response.read(400_000).decode("utf-8","replace")
            return {"url":url,"content":body,"untrusted":True}
        if name == "github.get":
            path=str(args.get("path","")).lstrip("/")
            if not path.startswith(("repos/","users/")): raise ValueError("only public GitHub API resource paths are allowed")
            url="https://api.github.com/"+path
            req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"ReBounce/0.9"})
            with urllib.request.urlopen(req,timeout=15) as response: return {"data":json.loads(response.read(400_000).decode("utf-8")),"source":url,"untrusted":True}
        if name.startswith("mcp."):
            server_id=str(args.get("server_id",""))
            server=_row(self.store,"SELECT * FROM mcp_servers WHERE id=? AND companion_id=? AND enabled=1",(server_id,cid))
            if not server: raise ValueError("enabled MCP server not found")
            mcp_args=json.loads(server["args_json"] or "[]")
            if name=="mcp.list_tools": return _mcp_exchange(str(server["command"]),list(mcp_args),"tools/list")
            if name=="mcp.call": return _mcp_exchange(str(server["command"]),list(mcp_args),"tools/call",{"name":str(args.get("name","")),"arguments":args.get("arguments",{})})
        raise ValueError("unsupported tool")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+","-",value.lower()).strip("-")[:80] or "project"


def list_approvals(store: SQLiteStore, cid: str) -> list[dict[str,Any]]:
    return _rows(store,"SELECT * FROM tool_approvals WHERE companion_id=? AND status='pending' ORDER BY created_at DESC",(str(cid),))


def resolve_approval(store: SQLiteStore, approval_id: str, approved: bool, companion_id: str | None = None) -> dict[str,Any]:
    if companion_id:
        row=_row(store,"SELECT * FROM tool_approvals WHERE id=? AND companion_id=?",(approval_id, str(companion_id)))
    else:
        row=_row(store,"SELECT * FROM tool_approvals WHERE id=?",(approval_id,))
    if not row: raise ValueError("approval not found")
    status="approved" if approved else "rejected"
    with store._connect() as con:
        con.execute("UPDATE tool_approvals SET status=?,resolved_at=? WHERE id=?",(status,now_iso(),approval_id))
    return {**row,"status":status,"resolved_at":now_iso()}


def compact_journal(store: SQLiteStore, cid: str, limit: int=100) -> list[dict[str,Any]]:
    rows=_rows(store,"SELECT id,event_type,data_json,created_at FROM events WHERE companion_id=? ORDER BY created_at DESC LIMIT ?",(str(cid),limit))
    out=[]
    for r in rows:
        try: data=json.loads(r["data_json"] or "{}")
        except Exception: data={}
        out.append({"id":r["id"],"event_type":r["event_type"],"data":data,"created_at":r["created_at"]})
    return out
