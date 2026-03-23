"""Tasks API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.tasks import services
from app.modules.tasks.models import FollowUpTask


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class FollowUpTaskRead(BaseModel):
    id: UUID
    pack_id: UUID
    lead_id: UUID | None
    task_type: str
    due_date: datetime
    status: str
    message_template: str
    template_key: str | None = None
    lead_name: str | None = None
    last_interaction_summary: str | None = None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


def _task_to_read(task: FollowUpTask, lead_name: str | None = None, last_interaction_summary: str | None = None) -> FollowUpTaskRead:
    return FollowUpTaskRead(
        id=task.id,
        pack_id=task.pack_id,
        lead_id=task.lead_id,
        task_type=task.task_type,
        due_date=task.due_date,
        status=task.status,
        message_template=task.message_template,
        template_key=getattr(task, "template_key", None),
        lead_name=lead_name,
        last_interaction_summary=last_interaction_summary,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


def _ensure_pack_access(db: Session, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


def _get_task_for_user_or_404(db: Session, task_id: UUID, user_id: UUID) -> FollowUpTask:
    task = db.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    if not task:
        raise NotFoundError("Task not found")
    _ensure_pack_access(db, task.pack_id, user_id)
    return task


@router.get("", response_model=list[FollowUpTaskRead])
def get_tasks(
    pack_id: UUID = Query(...),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get follow-up tasks for a pack. Sorted: overdue, due today, upcoming."""
    from app.modules.clients.models import Lead

    _ensure_pack_access(db, pack_id, current_user.id)

    if status == "overdue":
        tasks = services.get_overdue_tasks(db, pack_id)
    else:
        tasks = services.get_pending_tasks_sorted_for_queue(db, pack_id)

    lead_ids = [t.lead_id for t in tasks if t.lead_id is not None]
    leads_map = {}
    if lead_ids:
        leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        leads_map = {l.id: (l.name or "Lead", l.summary) for l in leads}

    return [
        _task_to_read(
            t,
            lead_name=leads_map.get(t.lead_id, (None, None))[0] if t.lead_id else None,
            last_interaction_summary=leads_map.get(t.lead_id, (None, None))[1] if t.lead_id else None,
        )
        for t in tasks
    ]


@router.post("/{task_id}/complete", response_model=FollowUpTaskRead)
def complete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark task as completed."""
    _get_task_for_user_or_404(db, task_id, current_user.id)
    task = services.complete_task(db, task_id)
    lead_name = None
    last_interaction_summary = None
    if task.lead_id:
        from app.modules.clients.models import Lead
        lead = db.query(Lead).filter(Lead.id == task.lead_id).first()
        if lead:
            lead_name = lead.name or "Lead"
            last_interaction_summary = lead.summary
    return _task_to_read(task, lead_name=lead_name, last_interaction_summary=last_interaction_summary)


@router.post("/{task_id}/skip", response_model=FollowUpTaskRead)
def skip_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark task as skipped."""
    _get_task_for_user_or_404(db, task_id, current_user.id)
    task = services.skip_task(db, task_id)
    lead_name = None
    last_interaction_summary = None
    if task.lead_id:
        from app.modules.clients.models import Lead
        lead = db.query(Lead).filter(Lead.id == task.lead_id).first()
        if lead:
            lead_name = lead.name or "Lead"
            last_interaction_summary = lead.summary
    return _task_to_read(task, lead_name=lead_name, last_interaction_summary=last_interaction_summary)
