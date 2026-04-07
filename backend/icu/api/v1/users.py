from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from icu.api.deps import get_current_user
from icu.db.session import get_session
from icu.models.user import User
from icu.schemas.auth import PresenceResponse, UserPublic
from icu.services import presence

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.get("/by-uin/{uin}", response_model=UserPublic)
async def get_by_uin(
    uin: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> User:
    u = await session.scalar(select(User).where(User.uin == uin, User.deleted_at.is_(None)))
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    return u


@router.get("/by-uin/{uin}/presence", response_model=PresenceResponse)
async def get_presence_by_uin(
    uin: int,
    _: Annotated[User, Depends(get_current_user)],
) -> PresenceResponse:
    online = await presence.is_uin_online(uin)
    return PresenceResponse(uin=uin, online=online)
