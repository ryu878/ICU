from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DirectConversationCreate(BaseModel):
    peer_uin: int = Field(gt=0)


class ConversationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    peer_uin: int
    peer_display_name: str | None
    created_at: datetime


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=16000)
    client_message_id: UUID


DeliveryStatus = Literal["sent", "delivered", "read"]


class MessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_uin: int
    body: str
    client_message_id: UUID
    created_at: datetime
    outgoing: bool
    delivery_status: DeliveryStatus | None = None


class MessageListResponse(BaseModel):
    messages: list[MessageItem]
    has_more: bool


class ReceiptBody(BaseModel):
    """Marks peer messages up to the given id as delivered and/or read (direct chat)."""

    delivered_up_to_message_id: int | None = Field(default=None, ge=1)
    read_up_to_message_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def at_least_one(self) -> ReceiptBody:
        if self.delivered_up_to_message_id is None and self.read_up_to_message_id is None:
            raise ValueError("delivered_up_to_message_id or read_up_to_message_id required")
        return self
