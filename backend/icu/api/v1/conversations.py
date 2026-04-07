from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from icu.api.deps import get_current_user
from icu.db.session import get_session
from icu.models.user import User
from icu.realtime.notify import publish_to_user
from icu.schemas.chat import (
    ConversationItem,
    DirectConversationCreate,
    MessageCreate,
    MessageItem,
    MessageListResponse,
    ReceiptBody,
)
from icu.services import chats as chat_svc

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationItem])
async def list_conversations(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ConversationItem]:
    rows = await chat_svc.list_direct_conversations(session, user.id)
    return [
        ConversationItem(
            id=c.id,
            kind=c.kind,
            peer_uin=p.uin,
            peer_display_name=p.display_name,
            created_at=c.created_at,
        )
        for c, p in rows
    ]


@router.post("/direct", response_model=ConversationItem, status_code=status.HTTP_201_CREATED)
async def open_direct(
    body: DirectConversationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ConversationItem:
    try:
        conv, peer = await chat_svc.get_or_create_direct(
            session,
            my_user_id=user.id,
            peer_uin=body.peer_uin,
        )
    except ValueError as e:
        code = str(e)
        if code == "peer_not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "peer_not_found")
        if code == "self_chat":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "self_chat")
        raise
    await session.commit()
    return ConversationItem(
        id=conv.id,
        kind=conv.kind,
        peer_uin=peer.uin,
        peer_display_name=peer.display_name,
        created_at=conv.created_at,
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> MessageListResponse:
    if not await chat_svc.user_in_conversation(session, conversation_id, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation_not_found")

    rows, has_more = await chat_svc.list_messages(
        session,
        conversation_id=conversation_id,
        before_id=before_id,
        limit=limit,
    )
    uins = await chat_svc.uin_map_for_users(session, [m.sender_id for m in rows])
    items = [chat_svc.build_message_item(user.id, m, uins) for m in rows]
    return MessageListResponse(messages=items, has_more=has_more)


@router.post("/{conversation_id}/messages", response_model=MessageItem, status_code=status.HTTP_201_CREATED)
async def post_message(
    conversation_id: int,
    body: MessageCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> MessageItem:
    if not await chat_svc.user_in_conversation(session, conversation_id, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation_not_found")

    msg = await chat_svc.send_message_idempotent(
        session,
        conversation_id=conversation_id,
        sender_id=user.id,
        client_message_id=body.client_message_id,
        body=body.body,
    )
    await session.commit()

    peer_id = await chat_svc.get_other_user_id(session, conversation_id, user.id)
    uins = await chat_svc.uin_map_for_users(session, [msg.sender_id])
    item_me = chat_svc.build_message_item(user.id, msg, uins)

    if peer_id is not None:
        uins2 = await chat_svc.uin_map_for_users(session, [msg.sender_id, peer_id])
        item_peer = chat_svc.build_message_item(peer_id, msg, uins2)
        await publish_to_user(
            peer_id,
            {
                "v": 1,
                "type": "event",
                "name": "new_message",
                "message": item_peer.model_dump(mode="json"),
            },
        )

    return item_me


@router.post("/{conversation_id}/receipts", status_code=status.HTTP_204_NO_CONTENT)
async def post_receipts(
    conversation_id: int,
    body: ReceiptBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    if not await chat_svc.user_in_conversation(session, conversation_id, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation_not_found")

    try:
        notifications, max_id = await chat_svc.apply_receipts(
            session,
            conversation_id=conversation_id,
            user_id=user.id,
            delivered_up_to_message_id=body.delivered_up_to_message_id,
            read_up_to_message_id=body.read_up_to_message_id,
        )
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation_not_found")
        raise

    await session.commit()

    for kind, peer_uid in notifications:
        await publish_to_user(
            peer_uid,
            {
                "v": 1,
                "type": "event",
                "name": "receipt",
                "kind": kind,
                "conversation_id": conversation_id,
                "up_to_message_id": max_id,
            },
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
