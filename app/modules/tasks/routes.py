"""Tasks API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.tasks import services


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class FollowUpTaskRead(BaseModel):
    id: UUID
    pack_id: UUID
    lead_id: UUID | None
    task_type: str
    due_date: datetime
    status: str
    message_template: str
    created_at: datetime
    completed_at: datetime | None
    
    class Config:
        from_attributes = True


@router.get("", response_model=list[FollowUpTaskRead])
def get_tasks(
    pack_id: UUID = Query(...),
    status: str | None = Query(None),
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get follow-up tasks for a pack."""
    if status == "pending":
        tasks = services.get_pending_tasks(db, pack_id)
    elif status == "overdue":
        tasks = services.get_overdue_tasks(db, pack_id)
    else:
        # Get all pending by default
        tasks = services.get_pending_tasks(db, pack_id)
    return tasks


@router.post("/{task_id}/complete", response_model=FollowUpTaskRead)
def complete_task(
    task_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark task as completed."""
    task = services.complete_task(db, task_id)
    return task


@router.post("/{task_id}/skip", response_model=FollowUpTaskRead)
def skip_task(
    task_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark task as skipped."""
    task = services.skip_task(db, task_id)
    return task
