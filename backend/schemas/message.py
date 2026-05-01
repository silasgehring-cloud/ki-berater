from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageExchange(BaseModel):
    """A user-message + the AI's reply, returned by /conversations and /messages."""

    user_message: MessageRead
    assistant_message: MessageRead
