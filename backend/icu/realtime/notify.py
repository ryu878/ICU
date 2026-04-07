from __future__ import annotations

import json
from typing import Any

from icu.redis_client import get_redis

CHANNEL_USER = "icu:u:{user_id}"


async def publish_to_user(user_id: int, payload: dict[str, Any]) -> None:
    r = get_redis()
    await r.publish(CHANNEL_USER.format(user_id=user_id), json.dumps(payload, default=str))
