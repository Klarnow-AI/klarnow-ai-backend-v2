"""Chat services: conversations and messages."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.chat.models import Conversation, Message
from app.modules.packs.services import get_pack_for_user


TITLE_MAX_LEN = 80


@log_service_action()
def list_conversations(
    db: Session,
    user_id: UUID,
    pack_id: UUID | None = None,
    limit: int = 50,
) -> list[Conversation]:
    q = db.query(Conversation).filter(Conversation.user_id == user_id)
    if pack_id is not None:
        q = q.filter(Conversation.pack_id == pack_id)
    return q.order_by(Conversation.updated_at.desc()).limit(limit).all()


@log_service_action()
def get_first_message_titles(
    db: Session,
    conversation_ids: list[UUID],
) -> dict[UUID, str | None]:
    """Return mapping of conversation_id -> first message content (truncated), or None if no messages."""
    if not conversation_ids:
        return {}
    messages = (
        db.query(Message)
        .filter(Message.conversation_id.in_(conversation_ids))
        .order_by(Message.conversation_id, Message.created_at.asc())
        .all()
    )
    title_map: dict[UUID, str | None] = {}
    for m in messages:
        if m.conversation_id not in title_map:
            raw = (m.content or "").strip()
            title_map[m.conversation_id] = raw[:TITLE_MAX_LEN] if raw else None
    return title_map


@log_service_action()
def get_conversation_for_user(
    db: Session,
    conversation_id: UUID,
    user_id: UUID,
) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )


@log_service_action()
def delete_conversation(
    db: Session,
    conversation_id: UUID,
    user_id: UUID,
) -> bool:
    """Delete a conversation owned by the user. Returns True if deleted, False if not found."""
    conv = get_conversation_for_user(db, conversation_id, user_id)
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True


@log_service_action()
def create_conversation(
    db: Session,
    user_id: UUID,
    pack_id: UUID | None = None,
) -> Conversation:
    if pack_id:
        pack = get_pack_for_user(db, pack_id, user_id)
        if not pack:
            raise ValueError("Pack not found or access denied")
    conv = Conversation(user_id=user_id, pack_id=pack_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@log_service_action()
def get_messages(
    db: Session,
    conversation_id: UUID,
    user_id: UUID,
    limit: int = 100,
) -> list[Message]:
    conv = get_conversation_for_user(db, conversation_id, user_id)
    if not conv:
        return []
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )
