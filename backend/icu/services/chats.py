from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from icu.models.conversation import Conversation, ConversationMember, DirectConversation
from icu.models.message import Message
from icu.models.user import User
from icu.schemas.chat import DeliveryStatus, MessageItem


async def get_other_user_id(session: AsyncSession, conversation_id: int, user_id: int) -> int | None:
    return await session.scalar(
        select(ConversationMember.user_id).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id != user_id,
        ),
    )


async def get_peer_by_uin(session: AsyncSession, uin: int) -> User | None:
    return await session.scalar(select(User).where(User.uin == uin, User.deleted_at.is_(None)))


async def user_in_conversation(session: AsyncSession, conversation_id: int, user_id: int) -> bool:
    row = await session.scalar(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
        ),
    )
    return row is not None


async def get_or_create_direct(
    session: AsyncSession,
    *,
    my_user_id: int,
    peer_uin: int,
) -> tuple[Conversation, User]:
    peer = await get_peer_by_uin(session, peer_uin)
    if peer is None:
        raise ValueError("peer_not_found")
    if peer.id == my_user_id:
        raise ValueError("self_chat")

    low, high = sorted([my_user_id, peer.id])
    existing = await session.scalar(
        select(DirectConversation).where(
            DirectConversation.user_low_id == low,
            DirectConversation.user_high_id == high,
        ),
    )
    if existing is not None:
        conv = await session.get(Conversation, existing.conversation_id)
        assert conv is not None
        return conv, peer

    conv = Conversation(kind="direct")
    session.add(conv)
    await session.flush()

    session.add(
        DirectConversation(
            conversation_id=conv.id,
            user_low_id=low,
            user_high_id=high,
        ),
    )
    session.add(ConversationMember(conversation_id=conv.id, user_id=my_user_id))
    session.add(ConversationMember(conversation_id=conv.id, user_id=peer.id))
    await session.flush()
    return conv, peer


async def list_direct_conversations(
    session: AsyncSession,
    user_id: int,
) -> list[tuple[Conversation, User]]:
    me_m = aliased(ConversationMember)
    peer_m = aliased(ConversationMember)
    peer_u = aliased(User)
    q = (
        select(Conversation, peer_u)
        .join(me_m, and_(me_m.conversation_id == Conversation.id, me_m.user_id == user_id))
        .join(
            peer_m,
            and_(peer_m.conversation_id == Conversation.id, peer_m.user_id != user_id),
        )
        .join(peer_u, peer_u.id == peer_m.user_id)
        .where(Conversation.kind == "direct")
        .order_by(Conversation.id.desc())
    )
    r = await session.execute(q)
    return list(r.all())


async def list_messages(
    session: AsyncSession,
    *,
    conversation_id: int,
    before_id: int | None,
    limit: int,
) -> tuple[list[Message], bool]:
    lim = min(max(limit, 1), 100)
    q = select(Message).where(Message.conversation_id == conversation_id)
    if before_id is not None:
        q = q.where(Message.id < before_id)
    q = q.order_by(Message.id.desc()).limit(lim + 1)
    rows = (await session.scalars(q)).all()
    has_more = len(rows) > lim
    rows = rows[:lim]
    rows = list(reversed(rows))
    return rows, has_more


async def send_message_idempotent(
    session: AsyncSession,
    *,
    conversation_id: int,
    sender_id: int,
    client_message_id: UUID,
    body: str,
) -> Message:
    existing = await session.scalar(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.client_message_id == client_message_id,
        ),
    )
    if existing is not None:
        return existing

    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        client_message_id=client_message_id,
        body=body,
    )
    session.add(msg)
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        got = await session.scalar(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.client_message_id == client_message_id,
            ),
        )
        if got is not None:
            return got
        raise
    return msg


async def uin_map_for_users(session: AsyncSession, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = await session.execute(select(User.id, User.uin).where(User.id.in_(user_ids)))
    return {row[0]: row[1] for row in rows.all()}


def _outgoing_status(msg: Message) -> DeliveryStatus:
    if msg.read_at is not None:
        return "read"
    if msg.delivered_at is not None:
        return "delivered"
    return "sent"


def build_message_item(viewer_user_id: int, msg: Message, uin_map: dict[int, int]) -> MessageItem:
    sender_uin = uin_map[msg.sender_id]
    outgoing = msg.sender_id == viewer_user_id
    ds: DeliveryStatus | None = _outgoing_status(msg) if outgoing else None
    return MessageItem(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender_uin=sender_uin,
        body=msg.body,
        client_message_id=msg.client_message_id,
        created_at=msg.created_at,
        outgoing=outgoing,
        delivery_status=ds,
    )


async def apply_receipts(
    session: AsyncSession,
    *,
    conversation_id: int,
    user_id: int,
    delivered_up_to_message_id: int | None,
    read_up_to_message_id: int | None,
) -> tuple[list[tuple[str, int]], int | None]:
    """Returns list of (kind, peer_user_id_to_notify) and max message id touched for receipts."""
    now = datetime.now(UTC)
    peer_id = await get_other_user_id(session, conversation_id, user_id)
    if peer_id is None:
        raise ValueError("not_found")

    max_id: int | None = None
    delivered_touched = False
    read_touched = False

    if delivered_up_to_message_id is not None:
        sc = await session.scalars(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.id <= delivered_up_to_message_id,
            ),
        )
        msgs = sc.all()
        for m in msgs:
            if m.delivered_at is None:
                m.delivered_at = now
                delivered_touched = True
            if max_id is None or m.id > max_id:
                max_id = m.id

    if read_up_to_message_id is not None:
        sc = await session.scalars(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.id <= read_up_to_message_id,
            ),
        )
        msgs = sc.all()
        for m in msgs:
            if m.read_at is None:
                m.read_at = now
                read_touched = True
            if m.delivered_at is None:
                m.delivered_at = now
                delivered_touched = True
            if max_id is None or m.id > max_id:
                max_id = m.id

    notifications: list[tuple[str, int]] = []
    if read_touched:
        notifications.append(("read", peer_id))
    elif delivered_touched:
        notifications.append(("delivered", peer_id))

    return notifications, max_id
