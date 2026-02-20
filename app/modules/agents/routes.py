"""Agents API: decision log (read-only for debugging and audits)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.agents.schemas import DecisionLogEntryRead, DecisionLogList
from app.modules.agents.services import list_decision_log_for_user
from app.modules.packs.models import User

router = APIRouter()


@router.get("/decision-log", response_model=DecisionLogList)
def list_decision_log(
    pack_id: UUID | None = Query(None, description="Filter by pack (must be user's pack)"),
    limit: int = Query(50, ge=1, le=200, description="Max entries"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List decision log entries for the current user's packs. For debugging and audits."""
    items = list_decision_log_for_user(db, current_user.id, pack_id=pack_id, limit=limit)
    return DecisionLogList(
        items=[DecisionLogEntryRead.model_validate(e) for e in items],
        total=len(items),
    )
