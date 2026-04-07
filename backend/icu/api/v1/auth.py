from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from icu.config import settings
from icu.db.session import get_session
from icu.schemas.auth import (
    LogoutBody,
    RefreshBody,
    RequestOtpBody,
    RequestOtpResponse,
    TokenPairResponse,
    UserPublic,
    VerifyOtpBody,
    VerifyOtpResponse,
)
from icu.services import auth_flow
from icu.services import tokens as token_svc

router = APIRouter(prefix="/auth", tags=["auth"])

_OTP_ERRORS = {
    "locked": (status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts"),
    "cooldown": (status.HTTP_429_TOO_MANY_REQUESTS, "cooldown"),
    "hourly_limit": (status.HTTP_429_TOO_MANY_REQUESTS, "hourly_limit"),
    "ip_limit": (status.HTTP_429_TOO_MANY_REQUESTS, "ip_limit"),
    "invalid_email": (status.HTTP_400_BAD_REQUEST, "invalid_email"),
}


@router.post("/request-otp", response_model=RequestOtpResponse)
async def request_otp(
    body: RequestOtpBody,
    request: Request,
) -> RequestOtpResponse:
    client_ip = request.client.host if request.client else None
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    result = await auth_flow.request_otp(str(body.email), client_ip)
    if not result.ok:
        code, detail = _OTP_ERRORS.get(result.reason or "", (status.HTTP_400_BAD_REQUEST, result.reason))
        raise HTTPException(code, detail)
    return RequestOtpResponse(dev_code=result.dev_code)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    body: VerifyOtpBody,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VerifyOtpResponse:
    ua = request.headers.get("user-agent")
    out = await auth_flow.verify_otp_and_login(
        session,
        email=str(body.email),
        code=body.code,
        device_id=body.device_id,
        user_agent=ua,
    )
    if not out.ok:
        _map = {
            "locked": (status.HTTP_429_TOO_MANY_REQUESTS, "locked"),
            "no_code": (status.HTTP_400_BAD_REQUEST, "no_code"),
            "wrong_code": (status.HTTP_400_BAD_REQUEST, "wrong_code"),
            "invalid_email": (status.HTTP_400_BAD_REQUEST, "invalid_email"),
            "invalid_state": (status.HTTP_400_BAD_REQUEST, "invalid_state"),
            "account_disabled": (status.HTTP_403_FORBIDDEN, "account_disabled"),
        }
        code, detail = _map.get(out.error or "", (status.HTTP_400_BAD_REQUEST, out.error))
        raise HTTPException(code, detail)
    assert out.user is not None and out.access_token and out.refresh_token
    await session.commit()
    return VerifyOtpResponse(
        access_token=out.access_token,
        refresh_token=out.refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic(
            uin=out.user.uin,
            email=out.user.email,
            display_name=out.user.display_name,
        ),
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshBody,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenPairResponse:
    ua = request.headers.get("user-agent")
    rotated = await token_svc.rotate_refresh_token(
        session,
        raw_refresh=body.refresh_token,
        device_id=body.device_id,
        user_agent=ua,
    )
    if rotated is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh")
    new_refresh, user = rotated
    access = token_svc.create_access_token(user=user)
    await session.commit()
    return TokenPairResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutBody,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    ok = await token_svc.revoke_refresh_token(session, body.refresh_token)
    await session.commit()
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_token")
