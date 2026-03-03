"""Chat API: conversations, messages, Use / Preview / Apply."""

import uuid as uuid_lib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import BadRequestError, NotFoundError
from app.core.storage import upload_file as storage_upload_file
from app.modules.packs.models import User
from app.modules.chat.models import ChatAttachment
from app.modules.chat.schemas import (
    ChatAttachmentRead,
    ConversationCreate,
    ConversationListItem,
    ConversationList,
    ConversationRead,
    MessageList,
    MessageRead,
    SendMessageBody,
    SendMessageResponse,
    SuggestedPromptsResponse,
)
from app.modules.chat.services import (
    create_conversation,
    delete_conversation,
    get_first_message_titles,
    get_conversation_for_user,
    get_messages,
    list_conversations,
)
from app.modules.chat.orchestrator_chat import run_chat_turn, run_chat_turn_stream
from app.modules.chat.prompt_suggestions import suggest_pack_chat_prompts

router = APIRouter()

TEXT_ATTACHMENT_EXTENSIONS = {
    "txt",
    "md",
    "markdown",
    "csv",
    "json",
    "xml",
    "yaml",
    "yml",
    "html",
    "htm",
    "py",
    "js",
    "ts",
    "tsx",
    "jsx",
    "css",
    "sql",
    "log",
}


def _safe_filename(name: str | None) -> str:
    raw = (name or "attachment").strip()
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in raw)
    safe = safe.strip("._")
    return (safe or "attachment")[:200]


def _is_text_attachment(file_name: str, content_type: str | None) -> bool:
    if content_type and content_type.lower().startswith("text/"):
        return True
    ext = Path(file_name).suffix.lower().lstrip(".")
    return ext in TEXT_ATTACHMENT_EXTENSIONS


def _extract_text_content(
    payload: bytes,
    file_name: str,
    content_type: str | None,
    max_chars: int,
) -> str | None:
    if not payload or not _is_text_attachment(file_name, content_type):
        return None
    decoded = payload.decode("utf-8", errors="replace").replace("\x00", " ").strip()
    if not decoded:
        return None
    return decoded[: max(500, max_chars)]


@router.post(
    "/conversations/{conversation_id}/attachments",
    response_model=ChatAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    conversation_id: UUID,
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload one file for chat context and return attachment metadata."""
    conv = get_conversation_for_user(db, conversation_id, current_user.id)
    if not conv:
        raise NotFoundError("Conversation not found")

    content = await file.read()
    if not content:
        raise BadRequestError("File is empty")

    settings = get_settings()
    max_bytes = max(1, settings.chat_attachment_max_size_mb) * 1024 * 1024
    if len(content) > max_bytes:
        raise BadRequestError(
            f"File too large. Max size is {settings.chat_attachment_max_size_mb}MB."
        )

    safe_name = _safe_filename(file.filename)
    key = f"chat/attachments/{conversation_id}/{uuid_lib.uuid4().hex}_{safe_name}"
    uploaded_key = storage_upload_file(key, content, content_type=file.content_type)
    text_content = _extract_text_content(
        payload=content,
        file_name=safe_name,
        content_type=file.content_type,
        max_chars=settings.chat_attachment_max_text_chars,
    )

    attachment = ChatAttachment(
        conversation_id=conversation_id,
        user_id=current_user.id,
        file_name=safe_name,
        content_type=file.content_type,
        size_bytes=len(content),
        storage_key=uploaded_key,
        text_content=text_content,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return ChatAttachmentRead(
        id=attachment.id,
        conversation_id=attachment.conversation_id,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        has_text_content=bool(attachment.text_content),
        created_at=attachment.created_at,
    )


@router.get("/packs/{pack_id}/suggested-prompts", response_model=SuggestedPromptsResponse)
def get_suggested_prompts(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return up to 3 contextual chat starter prompts for a pack."""
    try:
        prompts = suggest_pack_chat_prompts(db, current_user.id, pack_id)
    except ValueError as e:
        raise NotFoundError(str(e))
    return SuggestedPromptsResponse(prompts=prompts)


@router.get("/conversations", response_model=ConversationList)
def list_my_conversations(
    pack_id: UUID | None = Query(None, description="Filter by pack"),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List conversations for the current user, optionally scoped to a pack."""
    conversations = list_conversations(
        db, current_user.id, pack_id=pack_id, limit=limit
    )
    conv_ids = [c.id for c in conversations]
    titles = get_first_message_titles(db, conv_ids)
    items = [
        ConversationListItem(
            **ConversationRead.model_validate(c).model_dump(),
            title=titles.get(c.id),
        )
        for c in conversations
    ]
    return ConversationList(items=items, total=len(items))


@router.post("/conversations", response_model=ConversationRead)
def create_conversation_route(
    body: ConversationCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation (global or pack-scoped)."""
    try:
        conv = create_conversation(
            db,
            current_user.id,
            pack_id=body.pack_id,
            day_context=body.day_context,
        )
    except ValueError as e:
        raise NotFoundError(str(e))
    return ConversationRead.model_validate(conv)


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a conversation by id."""
    conv = get_conversation_for_user(db, conversation_id, current_user.id)
    if not conv:
        raise NotFoundError("Conversation not found")
    return ConversationRead.model_validate(conv)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation_route(
    conversation_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation and its messages."""
    if not delete_conversation(db, conversation_id, current_user.id):
        raise NotFoundError("Conversation not found")


@router.get("/conversations/{conversation_id}/messages", response_model=MessageList)
def list_messages(
    conversation_id: UUID,
    limit: int = Query(100, ge=1, le=200),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List messages in a conversation (chronological)."""
    conv = get_conversation_for_user(db, conversation_id, current_user.id)
    if not conv:
        raise NotFoundError("Conversation not found")
    items = get_messages(db, conversation_id, current_user.id, limit=limit)
    return MessageList(
        items=[MessageRead.model_validate(m) for m in items],
        total=len(items),
    )


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: UUID,
    body: SendMessageBody,
    stream: bool = Query(
        False,
        description="If true, return SSE stream (events: status, chunk, done, error).",
    ),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and get Klaro's reply.
    - mode=use: run tools and return outcome (new version created).
    - mode=preview: return proposed tool_calls without executing.
    - mode=apply: execute tool_calls from the message given in apply_to_message_id.
    - stream=true: response is SSE with status/chunk/done/error events.
    """
    conv = get_conversation_for_user(db, conversation_id, current_user.id)
    if not conv:
        raise NotFoundError("Conversation not found")
    if stream:
        def sse_stream():
            for chunk in run_chat_turn_stream(
                db=db,
                user_id=current_user.id,
                conversation_id=conversation_id,
                pack_id=conv.pack_id,
                user_content=body.content,
                mode=body.mode,
                apply_to_message_id=body.apply_to_message_id,
                attachment_ids=body.attachment_ids,
            ):
                yield chunk
        return StreamingResponse(
            sse_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    try:
        result = run_chat_turn(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            pack_id=conv.pack_id,
            user_content=body.content,
            mode=body.mode,
            apply_to_message_id=body.apply_to_message_id,
            attachment_ids=body.attachment_ids,
        )
    except ValueError as e:
        raise NotFoundError(str(e))
    return SendMessageResponse(
        assistant_content=result.get("assistant_content", ""),
        message_id=result.get("message_id"),
        tool_calls=result.get("tool_calls"),
        tool_results=result.get("tool_results"),
        action_chips=result.get("action_chips"),
        references=result.get("references"),
        preview=result.get("preview", False),
    )
