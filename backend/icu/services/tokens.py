import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from icu.config import settings
from icu.models.refresh_token import RefreshToken
from icu.models.user import User


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_access_token(*, user: User) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "uin": user.uin,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def verify_access_token(token: str) -> dict | None:
    try:
        payload = decode_access_token(token)
        if payload.get("typ") != "access":
            return None
        return payload
    except JWTError:
        return None


async def issue_refresh_token(
    session: AsyncSession,
    *,
    user: User,
    device_id: str | None,
    user_agent: str | None,
) -> tuple[str, RefreshToken]:
    raw = secrets.token_urlsafe(48)
    token_hash = _hash_refresh(raw)
    now = datetime.now(UTC)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    row = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        device_id=device_id,
        user_agent=user_agent,
        expires_at=expires,
    )
    session.add(row)
    await session.flush()
    return raw, row


async def rotate_refresh_token(
    session: AsyncSession,
    *,
    raw_refresh: str,
    device_id: str | None,
    user_agent: str | None,
) -> tuple[str, User] | None:
    th = _hash_refresh(raw_refresh)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == th),
    )
    if row is None:
        return None
    now = datetime.now(UTC)
    if row.revoked_at is not None or row.expires_at <= now:
        return None

    row.revoked_at = now
    user = await session.get(User, row.user_id)
    if user is None or user.deleted_at is not None:
        return None

    raw_new, _ = await issue_refresh_token(
        session,
        user=user,
        device_id=device_id or row.device_id,
        user_agent=user_agent or row.user_agent,
    )
    return raw_new, user


async def revoke_refresh_token(session: AsyncSession, raw_refresh: str) -> bool:
    th = _hash_refresh(raw_refresh)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == th),
    )
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = datetime.now(UTC)
    return True
