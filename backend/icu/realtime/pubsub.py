from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import redis.asyncio as redis

from icu.config import settings
from icu.realtime.manager import manager

if TYPE_CHECKING:
    pass

log = logging.getLogger("icu.pubsub")

_stop: asyncio.Event | None = None
_task: asyncio.Task[None] | None = None
_redis: redis.Redis | None = None


async def _listen_loop(r: redis.Redis) -> None:
    pubsub = r.pubsub()
    await pubsub.psubscribe("icu:u:*")
    log.info("Redis pubsub subscribed icu:u:*")
    assert _stop is not None
    while not _stop.is_set():
        try:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.warning("pubsub error: %s", e)
            await asyncio.sleep(0.5)
            continue
        if msg is None or msg["type"] != "pmessage":
            continue
        data = msg.get("data")
        if data is None:
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        ch = msg.get("channel")
        if ch is None:
            continue
        if isinstance(ch, bytes):
            ch = ch.decode()
        parts = ch.split(":")
        if len(parts) < 3:
            continue
        try:
            uid = int(parts[-1])
        except ValueError:
            continue
        await manager.send_json_user(uid, payload)
    try:
        await pubsub.close()
    except Exception:
        pass


async def start_pubsub_listener() -> None:
    global _stop, _task, _redis
    if _task is not None:
        return
    _stop = asyncio.Event()
    _redis = redis.from_url(settings.redis_url, decode_responses=True)
    assert _redis is not None
    _task = asyncio.create_task(_listen_loop(_redis))


async def stop_pubsub_listener() -> None:
    global _task, _stop, _redis
    if _stop is not None:
        _stop.set()
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
    _stop = None
    if _redis is not None:
        await _redis.aclose()
        _redis = None
