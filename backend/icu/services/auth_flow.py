from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from icu.models.user import User
from icu.redis_client import get_redis
from icu.services import otp as otp_svc
from icu.services import tokens as token_svc
from icu.services.uin import allocate_next_uin


async def request_otp(email: str, client_ip: str | None) -> otp_svc.OtpRequestResult:
    redis = get_redis()
    return await otp_svc.request_otp(redis, email, client_ip)


@dataclass
class VerifyLoginResult:
    ok: bool
    access_token: str | None = None
    refresh_token: str | None = None
    user: User | None = None
    error: str | None = None


async def verify_otp_and_login(
    session: AsyncSession,
    *,
    email: str,
    code: str,
    device_id: str | None,
    user_agent: str | None,
) -> VerifyLoginResult:
    redis = get_redis()
    check = await otp_svc.verify_otp_code(redis, email, code)
    if not check.ok:
        return VerifyLoginResult(False, error=check.reason)

    norm = otp_svc.normalize_email(email)
    user = await session.scalar(select(User).where(User.email == norm))
    if user is None:
        uin = await allocate_next_uin(session)
        user = User(
            uin=uin,
            email=norm,
            display_name=norm.split("@")[0],
        )
        session.add(user)
        await session.flush()
    elif user.deleted_at is not None:
        return VerifyLoginResult(False, error="account_disabled")

    access = token_svc.create_access_token(user=user)
    refresh, _ = await token_svc.issue_refresh_token(
        session,
        user=user,
        device_id=device_id,
        user_agent=user_agent,
    )
    return VerifyLoginResult(True, access_token=access, refresh_token=refresh, user=user)
