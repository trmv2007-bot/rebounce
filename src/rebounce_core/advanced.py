from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from .capabilities import load_policy
from .events import Event, EventType
from .permissions import ActionLevel
from .storage import SQLiteStore


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rows(store: SQLiteStore, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with store._connect() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def _row(store: SQLiteStore, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with store._connect() as con:
        value = con.execute(sql, params).fetchone()
    return dict(value) if value else None


def _setting(store: SQLiteStore, cid: str, key: str, default: Any) -> Any:
    row = _row(store, "SELECT value FROM companion_settings WHERE companion_id=? AND key=?", (cid, key))
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
               ON CONFLICT(companion_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (cid, key, json.dumps(value, ensure_ascii=False), now_iso()),
        )


def _guard(store: SQLiteStore, cid: str, resource: str, level: ActionLevel) -> None:
    if not load_policy(store, cid).decide(resource, level):
        raise PermissionError(f"permission denied: {resource} requires level {int(level)}")


def _event(store: SQLiteStore, user_id: str, cid: UUID, event_type: EventType, data: dict[str, Any]) -> None:
    store.save_event(Event(event_type, user_id, cid, data))


@dataclass(frozen=True, slots=True)
class VisionSession:
    id: str
    companion_id: str
    started_at: str
    expires_at: str
    allow_raw_capture: bool
    purpose: str
    active: bool


class VisionManager:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID):
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def status(self) -> dict[str, Any]:
        active = _row(
            self.store,
            "SELECT * FROM vision_sessions WHERE companion_id=? AND active=1 ORDER BY started_at DESC LIMIT 1",
            (str(self.companion_id),),
        )
        context = _row(
            "SELECT * FROM vision_context WHERE companion_id=? ORDER BY created_at DESC LIMIT 1"
            if active else "SELECT * FROM vision_context WHERE companion_id=? AND expires_at>? ORDER BY created_at DESC LIMIT 1",
            (str(self.companion_id),) if active else (str(self.companion_id), now_iso()),
        )
        return {
            "active_session": bool(active),
            "session": active,
            "context": context,
            "privacy": {
                "raw_capture_retained": False,
                "ephemeral_context": True,
                "screen_permission": load_policy(self.store, str(self.companion_id)).describe("screen"),
                "camera_permission": load_policy(self.store, str(self.companion_id)).describe("camera"),
            },
        }

    def start_session(self, minutes: int = 15, purpose: str = "intentional screen sharing", allow_raw_capture: bool = False) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "screen", ActionLevel.INFORMATIONAL)
        minutes = max(1, min(120, int(minutes)))
        expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        sid = str(uuid4())
        with self.store._connect() as con:
            con.execute("UPDATE vision_sessions SET active=0 WHERE companion_id=?", (str(self.companion_id),))
            con.execute(
                """INSERT INTO vision_sessions(id,companion_id,started_at,expires_at,allow_raw_capture,purpose,active)
                   VALUES (?,?,?,?,?,?,1)""",
                (sid, str(self.companion_id), now_iso(), expires.isoformat(), int(bool(allow_raw_capture)), purpose[:240],),
            )
        _event(self.store, self.user_id, self.companion_id, EventType.VISION_SESSION_STARTED, {"session_id": sid, "expires_at": expires.isoformat()})
        return _row(self.store, "SELECT * FROM vision_sessions WHERE id=?", (sid,)) or {}

    def observe(
        self,
        session_id: str,
        *,
        source: str = "screen",
        window_title: str = "",
        app_name: str = "",
        url: str = "",
        observation: str = "",
        screenshot_b64: str | None = None,
        ttl_seconds: int = 900,
    ) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "screen", ActionLevel.INFORMATIONAL)
        session = _row(self.store, "SELECT * FROM vision_sessions WHERE id=? AND companion_id=? AND active=1", (session_id, str(self.companion_id)))
        if not session:
            raise ValueError("vision session is not active")
        if datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            self.end_session(session_id)
            raise PermissionError("vision session expired")
        digest = hashlib.sha256(screenshot_b64.encode("utf-8")).hexdigest() if screenshot_b64 else None
        context_id = str(uuid4())
        expires = datetime.now(timezone.utc) + timedelta(seconds=max(30, min(3600, int(ttl_seconds))))
        with self.store._connect() as con:
            con.execute(
                """INSERT INTO vision_context(
                    id,companion_id,session_id,source,window_title,app_name,url,observation,content_hash,created_at,expires_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (context_id, str(self.companion_id), session_id, source[:40], window_title[:240], app_name[:120], url[:1000], observation[:8000], digest, now_iso(), expires.isoformat()),
            )
        _event(
            self.store,
            self.user_id,
            self.companion_id,
            EventType.VISION_OBSERVED,
            {"session_id": session_id, "context_id": context_id, "source": source, "stored_raw_capture": False},
        )
        return _row(self.store, "SELECT * FROM vision_context WHERE id=?", (context_id,)) or {}

    def end_session(self, session_id: str | None = None) -> None:
        with self.store._connect() as con:
            if session_id:
                con.execute("UPDATE vision_sessions SET active=0 WHERE id=? AND companion_id=?", (session_id, str(self.companion_id)))
            else:
                con.execute("UPDATE vision_sessions SET active=0 WHERE companion_id=?", (str(self.companion_id),))
            con.execute("DELETE FROM vision_context WHERE companion_id=? AND expires_at<=?", (str(self.companion_id), now_iso()))
        _event(self.store, self.user_id, self.companion_id, EventType.VISION_SESSION_ENDED, {"session_id": session_id})


class LongRunningAgent:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID):
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def state(self) -> dict[str, Any]:
        cid = str(self.companion_id)
        return {
            "plans": _rows(self.store, "SELECT * FROM agent_plans WHERE companion_id=? ORDER BY updated_at DESC", (cid,)),
            "jobs": _rows(self.store, "SELECT * FROM agent_jobs WHERE companion_id=? ORDER BY updated_at DESC LIMIT 200", (cid,)),
            "checkpoints": _rows(self.store, "SELECT * FROM agent_checkpoints WHERE companion_id=? ORDER BY created_at DESC LIMIT 200", (cid,)),
            "delegations": _rows(self.store, "SELECT * FROM agent_delegations WHERE companion_id=? ORDER BY created_at DESC LIMIT 100", (cid,)),
        }

    def create_plan(self, title: str, goal: str, approval_required: bool = True) -> dict[str, Any]:
        title, goal = title.strip(), goal.strip()
        if not title or not goal:
            raise ValueError("title and goal are required")
        pid = str(uuid4())
        status = "pending_approval" if approval_required else "active"
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO agent_plans(id,companion_id,title,goal,status,approval_required,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (pid, str(self.companion_id), title[:240], goal[:4000], status, int(bool(approval_required)), now_iso(), now_iso()),
            )
        _event(self.store, self.user_id, self.companion_id, EventType.AGENT_PLAN_CREATED, {"plan_id": pid, "status": status})
        return _row(self.store, "SELECT * FROM agent_plans WHERE id=?", (pid,)) or {}

    def add_job(self, plan_id: str, title: str, step: str, *, scheduled_at: str | None = None, max_attempts: int = 3) -> dict[str, Any]:
        plan = _row(self.store, "SELECT * FROM agent_plans WHERE id=? AND companion_id=?", (plan_id, str(self.companion_id)))
        if not plan:
            raise ValueError("plan not found")
        job_id = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                """INSERT INTO agent_jobs(
                    id,companion_id,plan_id,title,step,step_index,status,scheduled_at,attempts,max_attempts,last_error,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    job_id, str(self.companion_id), plan_id, title[:240], step[:4000], 0, "queued",
                    scheduled_at, 0, max(1, min(20, int(max_attempts))), "", now_iso(), now_iso(),
                ),
            )
            con.execute("UPDATE agent_plans SET updated_at=? WHERE id=?", (now_iso(), plan_id))
        return _row(self.store, "SELECT * FROM agent_jobs WHERE id=?", (job_id,)) or {}

    def approve_plan(self, plan_id: str, approved: bool) -> dict[str, Any]:
        plan = _row(self.store, "SELECT * FROM agent_plans WHERE id=? AND companion_id=?", (plan_id, str(self.companion_id)))
        if not plan:
            raise ValueError("plan not found")
        status = "active" if approved else "rejected"
        with self.store._connect() as con:
            con.execute("UPDATE agent_plans SET status=?,updated_at=? WHERE id=?", (status, now_iso(), plan_id))
        _event(self.store, self.user_id, self.companion_id, EventType.AGENT_PLAN_RESOLVED, {"plan_id": plan_id, "approved": approved})
        return _row(self.store, "SELECT * FROM agent_plans WHERE id=?", (plan_id,)) or {}

    def run_next(self, plan_id: str) -> dict[str, Any]:
        plan = _row(self.store, "SELECT * FROM agent_plans WHERE id=? AND companion_id=?", (plan_id, str(self.companion_id)))
        if not plan:
            raise ValueError("plan not found")
        if plan["status"] != "active":
            raise PermissionError("plan is not active")
        job = _row(
            self.store,
            """SELECT * FROM agent_jobs
               WHERE companion_id=? AND plan_id=? AND status='queued'
                 AND (scheduled_at IS NULL OR scheduled_at<=?)
               ORDER BY step_index ASC, created_at ASC LIMIT 1""",
            (str(self.companion_id), plan_id, now_iso()),
        )
        if not job:
            return {"status": "idle", "message": "No queued work for this plan."}
        self._update_job(job["id"], status="running", attempts=int(job["attempts"]) + 1)
        checkpoint_state = {
            "step": job["step"],
            "step_index": int(job["step_index"]),
            "checkpointed_at": now_iso(),
            "resumable": True,
        }
        checkpoint_id = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO agent_checkpoints(id,job_id,companion_id,step_index,state_json,note,created_at) VALUES (?,?,?,?,?,?,?)",
                (checkpoint_id, job["id"], str(self.companion_id), int(job["step_index"]), json.dumps(checkpoint_state), "Durable checkpoint created; next execution can resume from here.", now_iso()),
            )
            con.execute("UPDATE agent_jobs SET status='checkpointed',updated_at=? WHERE id=?", (now_iso(), job["id"]))
        _event(self.store, self.user_id, self.companion_id, EventType.AGENT_CHECKPOINT, {"job_id": job["id"], "checkpoint_id": checkpoint_id})
        return {"status": "checkpointed", "job": _row(self.store, "SELECT * FROM agent_jobs WHERE id=?", (job["id"],)) or {}, "checkpoint": _row(self.store, "SELECT * FROM agent_checkpoints WHERE id=?", (checkpoint_id,)) or {}}

    def recover(self) -> list[dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        stale = _rows(self.store, "SELECT * FROM agent_jobs WHERE companion_id=? AND status='running' AND updated_at<?", (str(self.companion_id), cutoff))
        for job in stale:
            self._update_job(job["id"], status="queued", last_error="Recovered after stale worker heartbeat")
        return stale

    def delegate(self, job_id: str, specialist: str, scope: str) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "delegation", ActionLevel.REVERSIBLE)
        if not _row(self.store, "SELECT id FROM agent_jobs WHERE id=? AND companion_id=?", (job_id, str(self.companion_id))):
            raise ValueError("job not found")
        did = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO agent_delegations(id,job_id,companion_id,specialist,scope,status,created_at) VALUES (?,?,?,?,?,?,?)",
                (did, job_id, str(self.companion_id), specialist[:120], scope[:2000], "proposed", now_iso()),
            )
        return _row(self.store, "SELECT * FROM agent_delegations WHERE id=?", (did,)) or {}

    def tick(self) -> None:
        self.recover()

    def _update_job(self, job_id: str, **fields: Any) -> None:
        allowed = {"status", "attempts", "last_error", "step_index", "scheduled_at"}
        parts, values = [], []
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError("invalid job field")
            parts.append(f"{key}=?")
            values.append(value)
        if not parts:
            return
        values.extend([now_iso(), job_id, str(self.companion_id)])
        with self.store._connect() as con:
            con.execute(f"UPDATE agent_jobs SET {', '.join(parts)}, updated_at=? WHERE id=? AND companion_id=?", tuple(values))


class DeviceSyncManager:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID):
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def state(self) -> dict[str, Any]:
        cid = str(self.companion_id)
        return {
            "devices": _rows(self.store, "SELECT * FROM devices WHERE companion_id=? ORDER BY last_seen DESC", (cid,)),
            "offline_queue": _rows(self.store, "SELECT * FROM offline_queue WHERE companion_id=? AND status='queued' ORDER BY created_at ASC", (cid,)),
            "recent_sync": _rows(self.store, "SELECT * FROM sync_events WHERE companion_id=? ORDER BY sequence DESC LIMIT 100", (cid,)),
        }

    def register(self, name: str, kind: str, platform: str, capabilities: list[str] | None = None) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "device_sync", ActionLevel.REVERSIBLE)
        device_id = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO devices(id,companion_id,name,kind,platform,capabilities_json,status,last_seen,sync_cursor,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (device_id, str(self.companion_id), name.strip()[:120], kind[:80], platform[:80], json.dumps(capabilities or []), "online", now_iso(), 0, now_iso()),
            )
        return _row(self.store, "SELECT * FROM devices WHERE id=?", (device_id,)) or {}

    def heartbeat(self, device_id: str, status: str = "online") -> dict[str, Any]:
        allowed = {"online", "offline", "sleeping", "syncing", "error"}
        if status not in allowed:
            raise ValueError("invalid device status")
        with self.store._connect() as con:
            con.execute("UPDATE devices SET status=?,last_seen=? WHERE id=? AND companion_id=?", (status, now_iso(), device_id, str(self.companion_id)))
        return _row(self.store, "SELECT * FROM devices WHERE id=?", (device_id,)) or {}

    def append_event(self, device_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "device_sync", ActionLevel.INFORMATIONAL)
        if not _row(self.store, "SELECT id FROM devices WHERE id=? AND companion_id=?", (device_id, str(self.companion_id))):
            raise ValueError("device not found")
        with self.store._connect() as con:
            current = con.execute("SELECT COALESCE(MAX(sequence),0)+1 AS n FROM sync_events WHERE companion_id=?", (str(self.companion_id),)).fetchone()["n"]
            seq = int(current)
            event_id = str(uuid4())
            con.execute(
                "INSERT INTO sync_events(id,companion_id,device_id,sequence,event_type,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (event_id, str(self.companion_id), device_id, seq, event_type[:120], json.dumps(payload, ensure_ascii=False), now_iso()),
            )
            con.execute("UPDATE devices SET sync_cursor=? WHERE id=?", (seq, device_id))
        return _row(self.store, "SELECT * FROM sync_events WHERE id=?", (event_id,)) or {}

    def pull_since(self, cursor: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        return _rows(self.store, "SELECT * FROM sync_events WHERE companion_id=? AND sequence>? ORDER BY sequence ASC LIMIT ?", (str(self.companion_id), max(0, int(cursor)), max(1, min(500, int(limit)))))

    def queue_offline(self, device_id: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        item_id = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO offline_queue(id,companion_id,device_id,operation,payload_json,status,created_at) VALUES (?,?,?,?,?,?,?)",
                (item_id, str(self.companion_id), device_id, operation[:120], json.dumps(payload, ensure_ascii=False), "queued", now_iso()),
            )
        return _row(self.store, "SELECT * FROM offline_queue WHERE id=?", (item_id,)) or {}

    def handoff(self, source_device: str, target_device: str | None, ttl_minutes: int = 10) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "device_sync", ActionLevel.REVERSIBLE)
        bundle = {
            "companion_id": str(self.companion_id),
            "issued_at": now_iso(),
            "conversation_cursor": _row(self.store, "SELECT COUNT(*) AS n FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.companion_id=?", (str(self.companion_id),))["n"],
            "memory_cursor": _row(self.store, "SELECT COUNT(*) AS n FROM memories WHERE companion_id=?", (str(self.companion_id),))["n"],
        }
        token = str(uuid4())
        expires = (datetime.now(timezone.utc) + timedelta(minutes=max(1, min(60, int(ttl_minutes))))).isoformat()
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO handoff_tokens(id,companion_id,source_device,target_device,expires_at,payload_json,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (token, str(self.companion_id), source_device, target_device, expires, json.dumps(bundle), "active", now_iso()),
            )
        return {"token": token, "expires_at": expires, "bundle": bundle}


class EmbodimentManager:
    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID):
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def state(self) -> dict[str, Any]:
        cid = str(self.companion_id)
        profile = _row(self.store, "SELECT * FROM embodiment_profiles WHERE companion_id=? ORDER BY updated_at DESC LIMIT 1", (cid,))
        room = _row(self.store, "SELECT * FROM room_states WHERE companion_id=?", (cid,))
        objects = _rows(self.store, "SELECT * FROM room_objects WHERE companion_id=? ORDER BY updated_at DESC", (cid,))
        return {"profile": profile, "room": room, "objects": objects}

    def configure(self, data: dict[str, Any]) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "avatar", ActionLevel.REVERSIBLE)
        pid = str(uuid4())
        current = self.state()["profile"] or {}
        profile = {
            "id": pid,
            "companion_id": str(self.companion_id),
            "profile_name": str(data.get("profile_name", current.get("profile_name", "ReBounce avatar")))[:120],
            "asset_kind": str(data.get("asset_kind", current.get("asset_kind", "css-orb")))[:80],
            "asset_ref": str(data.get("asset_ref", current.get("asset_ref", "")))[:500],
            "expression_set": str(data.get("expression_set", current.get("expression_set", "calm,joy,focus,curious")))[:1000],
            "animation_style": str(data.get("animation_style", current.get("animation_style", "subtle")))[:100],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO embodiment_profiles(id,companion_id,profile_name,asset_kind,asset_ref,expression_set,animation_style,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                tuple(profile.values()),
            )
        return profile

    def room(self, name: str = "Companion Room", theme: str = "midnight") -> dict[str, Any]:
        current = self.state()["room"] or {}
        room = {"companion_id": str(self.companion_id), "name": name[:120], "theme": theme[:80], "scene_json": current.get("scene_json", "{}"), "updated_at": now_iso()}
        with self.store._connect() as con:
            con.execute(
                """INSERT INTO room_states(companion_id,name,theme,scene_json,updated_at) VALUES (?,?,?,?,?)
                   ON CONFLICT(companion_id) DO UPDATE SET name=excluded.name,theme=excluded.theme,scene_json=excluded.scene_json,updated_at=excluded.updated_at""",
                tuple(room.values()),
            )
        return room

    def upsert_object(self, kind: str, name: str, state: dict[str, Any]) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "avatar", ActionLevel.REVERSIBLE)
        oid = str(uuid4())
        item = {"id": oid, "companion_id": str(self.companion_id), "kind": kind[:80], "name": name[:120], "state_json": json.dumps(state, ensure_ascii=False), "created_at": now_iso(), "updated_at": now_iso()}
        with self.store._connect() as con:
            con.execute("INSERT INTO room_objects(id,companion_id,kind,name,state_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", tuple(item.values()))
        return item


class SharedActivityManager:
    ALLOWED = {"watch", "listen", "game", "study", "creative"}

    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID):
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def state(self) -> dict[str, Any]:
        cid = str(self.companion_id)
        return {
            "activities": _rows(self.store, "SELECT * FROM shared_activities WHERE companion_id=? ORDER BY updated_at DESC LIMIT 100", (cid,)),
            "events": _rows(
                self.store,
                "SELECT * FROM activity_events WHERE companion_id=? ORDER BY created_at DESC LIMIT 200",
                (cid,),
            ),
        }

    def create(self, activity_type: str, title: str) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "shared_activities", ActionLevel.REVERSIBLE)
        if activity_type not in self.ALLOWED:
            raise ValueError("unsupported activity type")
        aid = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO shared_activities(id,companion_id,activity_type,title,status,state_json,started_at,ended_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (aid, str(self.companion_id), activity_type, title[:240], "active", json.dumps({}), now_iso(), None, now_iso(), now_iso()),
            )
        return _row(self.store, "SELECT * FROM shared_activities WHERE id=?", (aid,)) or {}

    def update(self, activity_id: str, status: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
        if status not in {"active", "paused", "completed", "cancelled"}:
            raise ValueError("invalid activity status")
        row = _row(self.store, "SELECT * FROM shared_activities WHERE id=? AND companion_id=?", (activity_id, str(self.companion_id)))
        if not row:
            raise ValueError("activity not found")
        with self.store._connect() as con:
            con.execute(
                "UPDATE shared_activities SET status=?,state_json=?,ended_at=?,updated_at=? WHERE id=?",
                (status, json.dumps(state or json.loads(row["state_json"] or "{}")), now_iso() if status in {"completed", "cancelled"} else None, now_iso(), activity_id),
            )
        return _row(self.store, "SELECT * FROM shared_activities WHERE id=?", (activity_id,)) or {}

    def add_event(self, activity_id: str, actor: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not _row(self.store, "SELECT id FROM shared_activities WHERE id=? AND companion_id=?", (activity_id, str(self.companion_id))):
            raise ValueError("activity not found")
        eid = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO activity_events(id,activity_id,companion_id,actor,event_type,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (eid, activity_id, str(self.companion_id), actor[:80], event_type[:120], json.dumps(payload, ensure_ascii=False), now_iso()),
            )
        return _row(self.store, "SELECT * FROM activity_events WHERE id=?", (eid,)) or {}


class PhysicalWorldManager:
    SAFE_DEVICES = {"display", "speaker", "light", "haptic", "sensor"}
    CONTROLLED_DEVICES = {"smart_home", "wearable", "robot"}

    def __init__(self, store: SQLiteStore, user_id: str, companion_id: UUID):
        self.store, self.user_id, self.companion_id = store, user_id, companion_id

    def state(self) -> dict[str, Any]:
        cid = str(self.companion_id)
        return {
            "devices": _rows(self.store, "SELECT * FROM physical_devices WHERE companion_id=? ORDER BY updated_at DESC", (cid,)),
            "commands": _rows(self.store, "SELECT * FROM physical_commands WHERE companion_id=? ORDER BY created_at DESC LIMIT 100", (cid,)),
            "wearable_context": _rows(self.store, "SELECT * FROM wearable_context WHERE companion_id=? AND expires_at>? ORDER BY created_at DESC LIMIT 50", (cid, now_iso())),
        }

    def register_device(self, name: str, kind: str, transport: str = "simulator", location: str = "", capabilities: list[str] | None = None) -> dict[str, Any]:
        if kind not in self.SAFE_DEVICES | self.CONTROLLED_DEVICES:
            raise ValueError("unsupported physical device kind")
        did = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                """INSERT INTO physical_devices(
                    id,companion_id,name,kind,capabilities_json,transport,enabled,location,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (did, str(self.companion_id), name[:120], kind, json.dumps(capabilities or []), transport[:80], 0, location[:160], now_iso(), now_iso()),
            )
        return _row(self.store, "SELECT * FROM physical_devices WHERE id=?", (did,)) or {}

    def enable_device(self, device_id: str, enabled: bool) -> dict[str, Any]:
        _guard(self.store, str(self.companion_id), "physical_devices", ActionLevel.REVERSIBLE)
        with self.store._connect() as con:
            con.execute("UPDATE physical_devices SET enabled=?,updated_at=? WHERE id=? AND companion_id=?", (int(bool(enabled)), now_iso(), device_id, str(self.companion_id)))
        return _row(self.store, "SELECT * FROM physical_devices WHERE id=?", (device_id,)) or {}

    def command(self, device_id: str, command: str, payload: dict[str, Any], requested_level: int = 3, approved: bool = False) -> dict[str, Any]:
        device = _row(self.store, "SELECT * FROM physical_devices WHERE id=? AND companion_id=?", (device_id, str(self.companion_id)))
        if not device:
            raise ValueError("physical device not found")
        if not device["enabled"]:
            raise PermissionError("physical device is disabled")
        level = ActionLevel(max(0, min(5, int(requested_level))))
        resource = "robotics" if device["kind"] == "robot" else ("wearable" if device["kind"] == "wearable" else "smart_home")
        policy = load_policy(self.store, str(self.companion_id))
        if not policy.decide(resource, level):
            raise PermissionError(f"permission denied: {resource}")
        status = "approved" if approved else ("pending_approval" if level >= ActionLevel.APPROVAL_REQUIRED else "queued")
        cid = str(uuid4())
        with self.store._connect() as con:
            con.execute(
                "INSERT INTO physical_commands(id,companion_id,device_id,command,payload_json,requested_level,status,created_at,resolved_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (cid, str(self.companion_id), device_id, command[:160], json.dumps(payload, ensure_ascii=False), int(level), status, now_iso(), now_iso() if approved else None),
            )
        if approved and device["transport"] == "simulator":
            status = "simulated"
            with self.store._connect() as con:
                con.execute("UPDATE physical_commands SET status=? WHERE id=?", (status, cid))
        _event(self.store, self.user_id, self.companion_id, EventType.PHYSICAL_COMMAND, {"command_id": cid, "device_id": device_id, "status": status})
        return _row(self.store, "SELECT * FROM physical_commands WHERE id=?", (cid,)) or {}

    def resolve_command(self, command_id: str, approved: bool) -> dict[str, Any]:
        row = _row(self.store, "SELECT * FROM physical_commands WHERE id=? AND companion_id=?", (command_id, str(self.companion_id)))
        if not row:
            raise ValueError("command not found")
        if row["status"] != "pending_approval":
            return row
        status = "rejected" if not approved else "approved"
        with self.store._connect() as con:
            con.execute("UPDATE physical_commands SET status=?,resolved_at=? WHERE id=?", (status, now_iso(), command_id))
        if approved:
            device = _row(self.store, "SELECT * FROM physical_devices WHERE id=?", (row["device_id"],))
            status = "simulated" if device and device["transport"] == "simulator" else "approved"
            with self.store._connect() as con:
                con.execute("UPDATE physical_commands SET status=? WHERE id=?", (status, command_id))
        return _row(self.store, "SELECT * FROM physical_commands WHERE id=?", (command_id,)) or {}
