import os
import asyncio
import hmac
import logging
from ipaddress import ip_address, ip_network

import aiomysql
from fastapi import FastAPI, Request, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "kuma")
DB_USER = os.getenv("DB_USER", "kuma")
DB_PASS = os.environ["DB_PASS"]
API_KEY = os.environ["API_KEY"]

ALLOWED_RANGES_RAW = os.getenv("ALLOWED_RANGES", "")
ALLOWED_RANGES = [
    ip_network(r.strip(), strict=False)
    for r in ALLOWED_RANGES_RAW.split(",") if r.strip()
] if ALLOWED_RANGES_RAW.strip() else []

QUERY_MONITORS = """
SELECT id, name, active, type, parent, weight
FROM monitor
ORDER BY weight ASC
"""

QUERY_LATEST_HEARTBEATS = """
SELECT h.monitor_id, h.status, h.time, h.msg
FROM heartbeat h
INNER JOIN (
    SELECT monitor_id, MAX(id) AS max_id
    FROM heartbeat
    GROUP BY monitor_id
) latest ON h.id = latest.max_id
"""

app = FastAPI(title="Kuma API Proxy")


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def check_ip(request: Request):
    if not ALLOWED_RANGES:
        return
    client = get_client_ip(request)
    try:
        addr = ip_address(client)
    except ValueError:
        raise HTTPException(403, "Forbidden")
    for net in ALLOWED_RANGES:
        if addr in net:
            return
    log.warning("Blocked request from %s", client)
    raise HTTPException(403, "Forbidden")


def check_api_key(request: Request):
    key = request.headers.get("X-API-Key", "")
    if not hmac.compare_digest(key, API_KEY):
        raise HTTPException(401, "Unauthorized")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/monitors")
async def get_monitors(request: Request):
    check_ip(request)
    check_api_key(request)

    try:
        conn = await asyncio.wait_for(
            aiomysql.connect(
                host=DB_HOST, port=DB_PORT, db=DB_NAME,
                user=DB_USER, password=DB_PASS,
                charset="utf8mb4", autocommit=True,
            ),
            timeout=5.0,
        )
    except Exception as e:
        log.error("DB connection failed: %s", e)
        log.error("DB connection failed: %s", e)
        raise HTTPException(502, "Database unavailable")

    try:
        async with conn.cursor() as cur:
            await cur.execute(QUERY_MONITORS)
            monitor_rows = await cur.fetchall()

            await cur.execute(QUERY_LATEST_HEARTBEATS)
            hb_rows = await cur.fetchall()

        monitors = [
            {
                "id": row[0], "name": row[1], "active": bool(row[2]),
                "type": row[3] or "", "parent": row[4], "weight": row[5] or 2000,
            }
            for row in monitor_rows
        ]

        heartbeats = {
            str(row[0]): {
                "monitor_id": row[0], "status": row[1],
                "time": str(row[2]) if row[2] else "", "msg": row[3] or "",
            }
            for row in hb_rows
        }

        return {"monitors": monitors, "heartbeats": heartbeats}
    except Exception as e:
        log.error("DB query failed: %s", e)
        log.error("DB query failed: %s", e)
        raise HTTPException(502, "Query error")
    finally:
        conn.close()
