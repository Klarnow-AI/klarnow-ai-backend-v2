"""Agents services: decision log listing (scoped to user's packs)."""

from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.logging import log_service_action
from app.modules.agents.models import DecisionLog
from app.modules.packs.services import list_packs_for_user


@log_service_action()
def list_decision_log_for_user(
    db: Session,
    user_id: UUID,
    pack_id: UUID | None = None,
    limit: int = 50,
) -> list[DecisionLog]:
    """List decision log entries for packs owned by the user. Optional pack_id filter."""
    packs = list_packs_for_user(db, user_id, include_archived=True)
    project_ids = [p.id for p in packs]
    if not project_ids:
        return []
    q = db.query(DecisionLog).filter(DecisionLog.pack_id.in_(project_ids))
    if pack_id is not None:
        if pack_id not in project_ids:
            return []
        q = q.filter(DecisionLog.pack_id == pack_id)
    q = q.order_by(desc(DecisionLog.created_at)).limit(limit)
    return q.all()
