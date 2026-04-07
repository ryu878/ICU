import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass

from redis.asyncio import Redis

from icu.config import settings


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_code(code: str) -> str:
    raw = f"{settings.otp_pepper}:{code}".encode()
    return hashlib.sha256(raw).hexdigest()


def _otp_key(email: str) -> str:
    return f"icu:otp:{normalize_email(email)}"


def _cooldown_key(email: str) -> str:
    return f"icu:otp:cooldown:{normalize_email(email)}"


def _hour_key(email: str) -> str:
    return f"icu:otp:hour:{normalize_email(email)}"


def _lock_key(email: str) -> str:
    return f"icu:otp:lock:{normalize_email(email)}"


def _ip_hour_key(ip: str) -> str:
    return f"icu:otp:ip:{ip}"


@dataclass
class OtpRequestResult:
    ok: bool
    reason: str | None = None
    dev_code: str | None = None  # only when dev_log_otp


async def request_otp(redis: Redis, email: str, client_ip: str | None) -> OtpRequestResult:
    norm = normalize_email(email)
    if not norm or "@" not in norm:
        return OtpRequestResult(False, "invalid_email")

    if await redis.exists(_lock_key(email)):
        return OtpRequestResult(False, "locked")

    if await redis.exists(_cooldown_key(email)):
        return OtpRequestResult(False, "cooldown")

    if client_ip:
        ip_key = _ip_hour_key(client_ip)
        ip_count = await redis.incr(ip_key)
        if ip_count == 1:
            await redis.expire(ip_key, 3600)
        if ip_count > 60:
            await redis.decr(ip_key)
            return OtpRequestResult(False, "ip_limit")

    hk = _hour_key(email)
    hour_count = await redis.incr(hk)
    if hour_count == 1:
        await redis.expire(hk, 3600)
    if hour_count > settings.otp_max_per_hour:
        await redis.decr(hk)
        return OtpRequestResult(False, "hourly_limit")

    code = f"{secrets.randbelow(900_000) + 100_000:06d}"
    payload = {
        "h": _hash_code(code),
        "a": 0,
    }
    pipe = redis.pipeline()
    pipe.set(_otp_key(email), json.dumps(payload), ex=settings.otp_ttl_seconds)
    pipe.set(_cooldown_key(email), "1", ex=settings.otp_cooldown_seconds)
    await pipe.execute()

    from icu.services import email_delivery

    await email_delivery.send_otp_email(norm, code)

    dev_code = code if settings.dev_log_otp else None
    return OtpRequestResult(True, dev_code=dev_code)


@dataclass
class OtpVerifyResult:
    ok: bool
    reason: str | None = None


async def verify_otp_code(redis: Redis, email: str, code: str) -> OtpVerifyResult:
    norm = normalize_email(email)
    if not norm:
        return OtpVerifyResult(False, "invalid_email")

    if await redis.exists(_lock_key(email)):
        return OtpVerifyResult(False, "locked")

    raw = await redis.get(_otp_key(email))
    if not raw:
        return OtpVerifyResult(False, "no_code")

    try:
        data = json.loads(raw)
        expected = data["h"]
        attempts = int(data.get("a", 0))
    except (json.JSONDecodeError, KeyError, TypeError):
        return OtpVerifyResult(False, "invalid_state")

    if hmac.compare_digest(expected, _hash_code(code.strip())):
        pipe = redis.pipeline()
        pipe.delete(_otp_key(email))
        pipe.delete(_cooldown_key(email))
        await pipe.execute()
        return OtpVerifyResult(True)

    attempts += 1
    if attempts >= settings.otp_max_attempts:
        await redis.set(_lock_key(email), "1", ex=settings.otp_lock_seconds)
        await redis.delete(_otp_key(email))
        return OtpVerifyResult(False, "locked")

    data["a"] = attempts
    ttl = await redis.ttl(_otp_key(email))
    if ttl < 0:
        ttl = settings.otp_ttl_seconds
    await redis.set(_otp_key(email), json.dumps(data), ex=ttl)
    return OtpVerifyResult(False, "wrong_code")
