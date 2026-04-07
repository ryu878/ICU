from icu.redis_client import get_redis

KEY = "icu:presence:uin:{uin}"
TTL_SECONDS = 60


async def touch_uin(uin: int) -> None:
    r = get_redis()
    await r.set(KEY.format(uin=uin), "1", ex=TTL_SECONDS)


async def is_uin_online(uin: int) -> bool:
    r = get_redis()
    return bool(await r.exists(KEY.format(uin=uin)))
