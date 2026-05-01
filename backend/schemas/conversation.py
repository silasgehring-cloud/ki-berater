from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.message import MessageRead


class ConversationCreate(BaseModel):
    visitor_id: str | None = Field(default=None, max_length=64)
    initial_message: str = Field(min_length=1, max_length=4000)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    visitor_id: str | None
    started_at: datetime
    ended_at: datetime | None
    converted: bool
    converted_at: datetime | None = None
    order_id: str | None = None
    order_total_eur: Decimal | None = None
    order_currency: str | None = None
    attribution_type: str | None = None


class ConversationCreated(BaseModel):
    """Response of POST /v1/conversations — convo + first exchange in one shot."""

    conversation: ConversationRead
    user_message: MessageRead
    assistant_message: MessageRead
