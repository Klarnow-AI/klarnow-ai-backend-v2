"""Chat API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import ReferenceSnippet


class ConversationCreate(BaseModel):
    pack_id: UUID | None = None
    day_context: int | None = None  # 0-3 for Day 0-3 conversational flow


class ConversationRead(BaseModel):
    id: UUID
    user_id: UUID
    pack_id: UUID | None = None
    day_context: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListItem(ConversationRead):
    """Conversation with optional title from first message."""

    title: str | None = None


class ConversationList(BaseModel):
    items: list[ConversationListItem]
    total: int


class MessageAttachmentRead(BaseModel):
    id: UUID
    file_name: str
    content_type: str | None = None
    size_bytes: int
    has_text_content: bool = False


class ChatAttachmentRead(MessageAttachmentRead):
    conversation_id: UUID
    created_at: datetime


class MessageRead(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str | None = None
    tool_calls: list | dict | None = None
    tool_results: dict | None = None
    attachments: list[MessageAttachmentRead] | None = None
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
    attachment_ids: list[UUID] = Field(default_factory=list)


class ChatActionChip(BaseModel):
    label: str
    href: str


class SendMessageResponse(BaseModel):
    assistant_content: str
    message_id: str | None = None
    tool_calls: list | None = None
    tool_results: dict | list | None = None
    action_chips: list[ChatActionChip] | None = None
    references: list[ReferenceSnippet] | None = None
    preview: bool = False


class SuggestedPromptsResponse(BaseModel):
    prompts: list[str]
