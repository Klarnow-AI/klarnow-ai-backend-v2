"""Chat API: conversations, messages, Use / Preview / Apply."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import User
from app.modules.chat.schemas import (
    ConversationCreate,
    ConversationListItem,
    ConversationList,
    ConversationRead,
    MessageList,
    MessageRead,
    SendMessageBody,
    SendMessageResponse,
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

router = APIRouter()


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
        conv = create_conversation(db, current_user.id, pack_id=body.pack_id)
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
    stream: bool = Query(False, description="If true, return SSE stream (one event with full response)"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and get Klaro's reply.
    - mode=use: run tools and return outcome (new version created).
    - mode=preview: return proposed tool_calls without executing.
    - mode=apply: execute tool_calls from the message given in apply_to_message_id.
    - stream=true: response is SSE (event: message, data: JSON).
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
        )
    except ValueError as e:
        raise NotFoundError(str(e))
    return SendMessageResponse(
        assistant_content=result.get("assistant_content", ""),
        message_id=result.get("message_id"),
        tool_calls=result.get("tool_calls"),
        tool_results=result.get("tool_results"),
        preview=result.get("preview", False),
    )
