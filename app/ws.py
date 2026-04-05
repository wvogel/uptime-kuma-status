import asyncio
import json
import logging
from fastapi import WebSocket

log = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        log.info("WebSocket client connected (%d total)", len(self._clients))

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        log.info("WebSocket client disconnected (%d total)", len(self._clients))

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        async with self._lock:
            dead = set()
            for ws in self._clients:
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.add(ws)
            self._clients -= dead
            if dead:
                log.info("Removed %d dead WebSocket connections", len(dead))

    @property
    def client_count(self) -> int:
        return len(self._clients)


ws_manager = WSManager()
