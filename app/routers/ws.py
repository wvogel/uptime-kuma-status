from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.cache import get_status_data
from app.ws import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        data = await get_status_data()
        await ws.send_json({"type": "full", "data": data})

        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
