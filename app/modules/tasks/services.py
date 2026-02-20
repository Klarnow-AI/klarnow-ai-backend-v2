"""Follow-up task service."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.tasks.models import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
    TASK_STATUS_SKIPPED,
    TASK_TYPE_INITIAL_CONTACT,
    TASK_TYPE_INVOICE_FOLLOWUP,
    TASK_TYPE_PROPOSAL_FOLLOWUP,
    FollowUpTask,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@log_service_action()
def create_followup_task(
    db: Session,
    pack_id: UUID,
    task_type: str,
    message_template: str,
    lead_id: UUID | None = None,
    due_hours: int = 24,
) -> FollowUpTask:
    """Create a follow-up task."""
    due_date = utc_now() + timedelta(hours=due_hours)
    
    task = FollowUpTask(
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=task_type,
        due_date=due_date,
        status=TASK_STATUS_PENDING,
        message_template=message_template,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@log_service_action()
def get_pending_tasks(db: Session, pack_id: UUID) -> list[FollowUpTask]:
    """Get all pending follow-up tasks for a pack."""
    return (
        db.query(FollowUpTask)
        .filter(FollowUpTask.pack_id == pack_id, FollowUpTask.status == TASK_STATUS_PENDING)
        .order_by(FollowUpTask.due_date.asc())
        .all()
    )


@log_service_action()
def get_overdue_tasks(db: Session, pack_id: UUID) -> list[FollowUpTask]:
    """Get overdue follow-up tasks for a pack."""
    now = utc_now()
    return (
        db.query(FollowUpTask)
        .filter(
            FollowUpTask.pack_id == pack_id,
            FollowUpTask.status == TASK_STATUS_PENDING,
            FollowUpTask.due_date < now,
        )
        .order_by(FollowUpTask.due_date.asc())
        .all()
    )


@log_service_action()
def complete_task(db: Session, task_id: UUID) -> FollowUpTask:
    """Mark a task as completed."""
    task = db.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    task.status = TASK_STATUS_COMPLETED
    task.completed_at = utc_now()
    db.commit()
    db.refresh(task)
    return task


@log_service_action()
def skip_task(db: Session, task_id: UUID) -> FollowUpTask:
    """Mark a task as skipped."""
    task = db.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    task.status = TASK_STATUS_SKIPPED
    db.commit()
    db.refresh(task)
    return task


@log_service_action()
def create_lead_contact_task(db: Session, pack_id: UUID, lead_id: UUID, lead_name: str) -> FollowUpTask:
    """Create initial contact task when lead is created."""
    template = f"Hey {lead_name}! Thanks for your interest. I'd love to learn more about what you're looking for. When's a good time to chat?"
    return create_followup_task(
        db,
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=TASK_TYPE_INITIAL_CONTACT,
        message_template=template,
        due_hours=0,  # Immediate
    )


@log_service_action()
def create_proposal_followup_task(db: Session, pack_id: UUID, lead_id: UUID | None, lead_name: str) -> FollowUpTask:
    """Create proposal follow-up task."""
    template = f"Hey {lead_name}, following up on the proposal I sent. Have you had a chance to review it? Happy to answer any questions."
    return create_followup_task(
        db,
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=TASK_TYPE_PROPOSAL_FOLLOWUP,
        message_template=template,
        due_hours=24,
    )


@log_service_action()
def create_invoice_followup_task(db: Session, pack_id: UUID, lead_id: UUID | None, lead_name: str) -> FollowUpTask:
    """Create invoice/payment follow-up task."""
    template = f"Hey {lead_name}, just checking in on the invoice. Let me know if you need anything to move forward."
    return create_followup_task(
        db,
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=TASK_TYPE_INVOICE_FOLLOWUP,
        message_template=template,
        due_hours=24,
    )
