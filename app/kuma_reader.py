import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)


@dataclass
class KumaMonitor:
    id: int
    name: str
    active: bool
    type: str
    parent: int | None
    weight: int


@dataclass
class KumaHeartbeat:
    monitor_id: int
    status: int  # 0=DOWN, 1=UP, 2=PENDING, 3=MAINTENANCE
    time: str
    msg: str


@dataclass
class KumaInstanceData:
    monitors: list[KumaMonitor]
    heartbeats: dict[int, KumaHeartbeat]  # monitor_id -> latest heartbeat
    reachable: bool
    error: str | None = None


async def read_kuma_instance(
    api_url: str, api_key: str, timeout: float = 10.0,
) -> KumaInstanceData:
    url = api_url.rstrip("/") + "/api/monitors"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers={"X-API-Key": api_key})
    except Exception as e:
        log.warning("Cannot connect to kuma-api at %s: %s", api_url, e)
        return KumaInstanceData(monitors=[], heartbeats={}, reachable=False, error=str(e))

    if resp.status_code != 200:
        msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
        log.warning("kuma-api error at %s: %s", api_url, msg)
        return KumaInstanceData(monitors=[], heartbeats={}, reachable=False, error=msg)

    try:
        data = resp.json()
        monitors = [
            KumaMonitor(
                id=m["id"], name=m["name"], active=bool(m["active"]),
                type=m.get("type", ""), parent=m.get("parent"), weight=m.get("weight", 2000),
            )
            for m in data.get("monitors", [])
        ]
        heartbeats = {
            int(k): KumaHeartbeat(
                monitor_id=int(k), status=v["status"],
                time=v.get("time", ""), msg=v.get("msg", ""),
            )
            for k, v in data.get("heartbeats", {}).items()
        }
        return KumaInstanceData(monitors=monitors, heartbeats=heartbeats, reachable=True)
    except Exception as e:
        log.error("Failed to parse kuma-api response from %s: %s", api_url, e)
        return KumaInstanceData(monitors=[], heartbeats={}, reachable=False, error=str(e))
