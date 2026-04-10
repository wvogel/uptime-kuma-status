import asyncio
import json
import logging
import sqlite3
from datetime import datetime

import redis.asyncio as redis

from app import config
from app.kuma_reader import read_kuma_instance, KumaInstanceData

log = logging.getLogger(__name__)

VALKEY_URL = "redis://valkey:6379/1"
VALKEY_KEY = "uptime-status:monitors"

STATUS_MAP = {0: "down", 1: "up", 2: "pending", 3: "maintenance"}


def _read_sqlite():
    """Read all config from SQLite (instances, hidden, incidents, settings, footer)."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        instances = [dict(r) for r in conn.execute(
            "SELECT * FROM kuma_instance ORDER BY position, name"
        ).fetchall()]
        hidden_set = {
            (r["instance_id"], r["kuma_monitor_id"])
            for r in conn.execute("SELECT instance_id, kuma_monitor_id FROM hidden_monitor").fetchall()
        }
        incidents = [dict(r) for r in conn.execute(
            "SELECT * FROM incident WHERE active = 1"
            " OR (resolved_at IS NOT NULL AND resolved_at > datetime('now', 'localtime', '-30 minutes'))"
            " ORDER BY position, occurred_at DESC"
        ).fetchall()]
        incident_updates = {}
        for r in conn.execute("SELECT * FROM incident_update ORDER BY created_at").fetchall():
            r = dict(r)
            incident_updates.setdefault(r["incident_id"], []).append(r)
        settings = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM setting").fetchall()}
        footer_items = [dict(r) for r in conn.execute(
            "SELECT * FROM footer_item ORDER BY position"
        ).fetchall()]
        return instances, hidden_set, incidents, incident_updates, settings, footer_items
    finally:
        conn.close()


def _build_tree(monitors, heartbeats, hidden_ids, inst_id):
    """Build monitor tree from raw data, filtering hidden, deriving status."""
    all_by_id = {m["id"]: m for m in monitors}

    active_cache = {}
    def is_effectively_active(mon_id, cache=None):
        if cache is None:
            cache = active_cache
        if mon_id in cache:
            return cache[mon_id]
        mon = all_by_id.get(mon_id)
        if not mon or not mon["active"]:
            cache[mon_id] = False
            return False
        if mon["parent"] and mon["parent"] in all_by_id:
            result = is_effectively_active(mon["parent"], cache)
        else:
            result = True
        cache[mon_id] = result
        return result

    def make_node(m):
        mid = m["id"]
        if not is_effectively_active(mid):
            status = "inactive"
        elif str(mid) in heartbeats:
            status = STATUS_MAP.get(heartbeats[str(mid)]["status"], "unknown")
        else:
            status = "unknown"
        return {
            "id": f"{inst_id}-{mid}",
            "kuma_id": mid,
            "name": m["name"],
            "status": status,
            "children": [],
        }

    visible_ids = {m["id"] for m in monitors} - hidden_ids

    def effective_parent(m):
        pid = m["parent"]
        while pid is not None:
            if pid in visible_ids:
                return pid
            parent = all_by_id.get(pid)
            if not parent:
                return None
            pid = parent["parent"]
        return None

    children_map = {}
    for m in monitors:
        if m["id"] not in visible_ids:
            continue
        ep = effective_parent(m)
        children_map.setdefault(ep, []).append(m)

    def build(parent_id):
        nodes = []
        for m in children_map.get(parent_id, []):
            node = make_node(m)
            node["children"] = build(m["id"])
            nodes.append(node)
        nodes.sort(key=lambda n: n["name"].lower())
        return nodes

    roots = build(None)

    # Derive group status from worst child
    priority = {"down": 0, "pending": 1, "unreachable": 2, "maintenance": 3, "unknown": 4, "inactive": 5, "up": 6}

    def derive_status(node):
        for c in node["children"]:
            derive_status(c)
        if node["children"]:
            mon = all_by_id.get(node["kuma_id"])
            if mon and mon.get("type") == "group":
                statuses = [c["status"] for c in node["children"]]
                if all(s == "up" for s in statuses):
                    node["status"] = "up"
                elif all(s == "down" for s in statuses):
                    node["status"] = "down"
                else:
                    node["status"] = "degraded"

    for r in roots:
        derive_status(r)

    return roots


class MonitorFetcher:
    """Runs in admin app only. Fetches from kuma-apis, writes to Valkey."""

    def __init__(self):
        self._task = None

    def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while True:
            try:
                await self._fetch_all()
            except Exception:
                log.exception("Fetch cycle failed")
            await asyncio.sleep(config.CACHE_INTERVAL)

    async def _fetch_all(self):
        from app.services.instance_service import decrypt_api_key

        instances, hidden_set, _, _, _, _ = _read_sqlite()
        log.info("Fetch cycle: %d instances, %d hidden", len(instances), len(hidden_set))

        results = []
        for inst in instances:
            api_key = decrypt_api_key(inst["api_key"])
            data = await read_kuma_instance(api_url=inst["api_url"], api_key=api_key)

            hidden_ids = {m.id for m in data.monitors if (inst["id"], m.id) in hidden_set}

            if data.reachable:
                monitors_raw = [
                    {"id": m.id, "name": m.name, "active": m.active, "type": m.type,
                     "parent": m.parent, "weight": m.weight}
                    for m in data.monitors
                ]
                heartbeats_raw = {
                    str(k): {"monitor_id": v.monitor_id, "status": v.status,
                             "time": v.time, "msg": v.msg}
                    for k, v in data.heartbeats.items()
                }
                groups = _build_tree(monitors_raw, heartbeats_raw, hidden_ids, inst["id"])
            else:
                groups = []

            results.append({
                "id": inst["id"],
                "name": inst["name"],
                "reachable": data.reachable,
                "error": data.error,
                "groups": groups,
            })

        # Write to Valkey
        r = redis.from_url(VALKEY_URL)
        try:
            await r.set(VALKEY_KEY, json.dumps(results))
            log.info("Wrote %d instances to Valkey", len(results))
        finally:
            await r.aclose()

    async def force_fetch(self):
        await self._fetch_all()


def _build_incident(inc: dict, updates: list[dict]) -> dict | None:
    """Build incident dict with resolved state and effective severity.
    Returns None if resolved more than 30 minutes ago."""
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%dT%H:%M")
    resolved_at = inc.get("resolved_at") or ""
    resolved = bool(resolved_at and resolved_at <= now_str)

    # Hide completely if resolved more than 30 minutes ago
    if resolved and resolved_at:
        try:
            resolved_dt = datetime.strptime(resolved_at[:16], "%Y-%m-%dT%H:%M")
            if (now - resolved_dt).total_seconds() > 1800:
                return None
        except ValueError:
            pass

    # Effective severity: last update with severity, or incident severity
    effective_severity = inc["severity"]
    for upd in updates:
        if upd.get("severity"):
            effective_severity = upd["severity"]

    return {
        "id": inc["id"],
        "title_de": inc["title_de"],
        "title_en": inc["title_en"],
        "content_de": inc["content_de"],
        "content_en": inc["content_en"],
        "severity": effective_severity,
        "original_severity": inc["severity"],
        "active": inc["active"] and not resolved,
        "resolved": resolved,
        "occurred_at": inc["occurred_at"] or "",
        "resolved_at": resolved_at,
        "created_at": inc["created_at"],
        "updated_at": inc["updated_at"],
        "updates": [
            {
                "id": u["id"],
                "message_de": u["message_de"],
                "message_en": u["message_en"],
                "severity": u.get("severity"),
                "created_at": u["created_at"],
            }
            for u in updates
        ],
    }


async def get_status_data() -> dict:
    """Read current status from Valkey + SQLite. Used by public and admin."""
    _, hidden_set, incidents, incident_updates, settings, footer_items = _read_sqlite()

    # Read monitor data from Valkey
    r = redis.from_url(VALKEY_URL)
    try:
        raw = await r.get(VALKEY_KEY)
    finally:
        await r.aclose()

    instances = json.loads(raw) if raw else []

    return {
        "instances": instances,
        "incidents": [
            built for inc in incidents
            if (built := _build_incident(inc, incident_updates.get(inc["id"], []))) is not None
        ],
        "settings": settings,
        "footer_items": [
            {
                "id": fi["id"],
                "label_de": fi["label_de"],
                "label_en": fi["label_en"],
                "url": fi["url"],
                "position": fi["position"],
            }
            for fi in footer_items
        ],
    }


# Singleton fetcher (only used by admin app)
monitor_fetcher = MonitorFetcher()
