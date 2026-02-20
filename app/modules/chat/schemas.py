"""Chat API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    pack_id: UUID | None = None


class ConversationRead(BaseModel):
    id: UUID
    user_id: UUID
    pack_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListItem(ConversationRead):
    """Conversation with optional title from first message."""

    title: str | None = None


class ConversationList(BaseModel):
    items: list[ConversationListItem]
    total: int


class MessageRead(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str | None = None
    tool_calls: list | dict | None = None
    tool_results: dict | None = None
    is_preview: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageList(BaseModel):
    items: list[MessageRead]
    total: int


class SendMessageBody(BaseModel):
    content: str
    mode: str = "use"  # use | preview | apply
    apply_to_message_id: UUID | None = None


class SendMessageResponse(BaseModel):
    assistant_content: str
    message_id: str | None = None
    tool_calls: list | None = None
    tool_results: list | None = None
    preview: bool = False
