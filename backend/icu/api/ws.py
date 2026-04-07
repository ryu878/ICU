from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from icu.db.session import async_session_factory
from icu.models.user import User
from icu.realtime.manager import manager
from icu.services import presence
from icu.services.tokens import verify_access_token

log = logging.getLogger("icu.ws")

router = APIRouter()


@router.websocket("/ws")
async def websocket_v1(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    payload = verify_access_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return
    try:
        uid = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        await websocket.close(code=4401)
        return

    async with async_session_factory() as session:
        user = await session.get(User, uid)
        if user is None or user.deleted_at is not None:
            await websocket.close(code=4401)
            return

    await manager.connect(user.id, websocket)
    await presence.touch_uin(user.uin)
    try:
        await websocket.send_json({"v": 1, "type": "welcome", "uin": user.uin})
        while True:
            raw = await websocket.receive_text()
            try:
                msg: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await presence.touch_uin(user.uin)
                await websocket.send_json({"v": 1, "type": "pong"})
    except WebSocketDisconnect:
        log.debug("ws disconnect user_id=%s", user.id)
    finally:
        manager.disconnect(user.id, websocket)
