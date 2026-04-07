from __future__ import annotations

from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class ConnectionManager:
    """In-process WebSocket fan-out per user (combined with Redis pub/sub for multi-worker)."""

    def __init__(self) -> None:
        self._by_user: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._by_user.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        conns = self._by_user.get(user_id)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            del self._by_user[user_id]

    async def send_json_user(self, user_id: int, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self._by_user.get(user_id, []):
            if ws.client_state != WebSocketState.CONNECTED:
                dead.append(ws)
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


manager = ConnectionManager()
