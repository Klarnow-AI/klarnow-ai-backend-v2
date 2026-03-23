"""Follow-up task service."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.tasks.models import (
    CHANNEL_DM,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
    TASK_STATUS_SKIPPED,
    TASK_TYPE_INITIAL_CONTACT,
    TASK_TYPE_INVOICE_FOLLOWUP,
    TASK_TYPE_PROPOSAL_FOLLOWUP,
    TEMPLATE_KEY_FOLLOWUP_2H,
    TEMPLATE_KEY_FOLLOWUP_24H,
    TEMPLATE_KEY_FOLLOWUP_72H,
    TEMPLATE_KEY_INVOICE_CHASE,
    TEMPLATE_KEY_PROPOSAL_FOLLOWUP,
    FollowUpTask,
)
from app.modules.tasks.templates import get_template


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@log_service_action()
def create_followup_task(
    db: Session,
    pack_id: UUID,
    task_type: str,
    message_template: str,
    lead_id: UUID | None = None,
    due_hours: int | None = 24,
    due_date: datetime | None = None,
    template_key: str | None = None,
    channel: str | None = CHANNEL_DM,
) -> FollowUpTask:
    """Create a follow-up task."""
    if due_date is None:
        due_date = utc_now() + timedelta(hours=due_hours or 24)

    task = FollowUpTask(
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=task_type,
        due_date=due_date,
        status=TASK_STATUS_PENDING,
        message_template=message_template,
        template_key=template_key,
        channel=channel,
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


def _is_overdue(d: datetime) -> bool:
    return d < utc_now()


def _is_due_today(d: datetime) -> bool:
    now = utc_now()
    return d.date() == now.date()


def _task_sort_key(task: FollowUpTask) -> tuple[int, datetime]:
    """Sort: 0=overdue, 1=due today, 2=upcoming; then by due_date."""
    if _is_overdue(task.due_date):
        return (0, task.due_date)
    if _is_due_today(task.due_date):
        return (1, task.due_date)
    return (2, task.due_date)


@log_service_action()
def get_pending_tasks_sorted_for_queue(db: Session, pack_id: UUID) -> list[FollowUpTask]:
    """Get pending tasks sorted: overdue first, then due today, then upcoming."""
    tasks = get_pending_tasks(db, pack_id)
    return sorted(tasks, key=_task_sort_key)


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
    """Mark a task as completed. Updates lead.last_contacted_at and lead.status to contacted if task has lead."""
    from app.modules.clients.models import Lead, LEAD_STATUS_CONTACTED

    task = db.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found")

    task.status = TASK_STATUS_COMPLETED
    task.completed_at = utc_now()

    if task.lead_id:
        lead = db.query(Lead).filter(Lead.id == task.lead_id).first()
        if lead:
            lead.last_contacted_at = utc_now()
            lead.status = LEAD_STATUS_CONTACTED

    db.commit()
    db.refresh(task)
    return task


@log_service_action()
def close_pending_tasks_for_lead(db: Session, lead_id: UUID) -> int:
    """Close all pending follow-up tasks for a lead. Used when lead becomes booked/won/lost."""
    count = (
        db.query(FollowUpTask)
        .filter(
            FollowUpTask.lead_id == lead_id,
            FollowUpTask.status == TASK_STATUS_PENDING,
        )
        .update({FollowUpTask.status: TASK_STATUS_SKIPPED}, synchronize_session="fetch")
    )
    db.commit()
    return count


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
def create_new_lead_followup_tasks(
    db: Session, pack_id: UUID, lead_id: UUID, lead_name: str
) -> list[FollowUpTask]:
    """Create 2h, 24h, 72h follow-up tasks when new lead is created. Per Follow-up MVP spec."""
    now = utc_now()
    tasks = []
    for template_key, hours in [
        (TEMPLATE_KEY_FOLLOWUP_2H, 2),
        (TEMPLATE_KEY_FOLLOWUP_24H, 24),
        (TEMPLATE_KEY_FOLLOWUP_72H, 72),
    ]:
        t = create_followup_task(
            db,
            pack_id=pack_id,
            lead_id=lead_id,
            task_type=TASK_TYPE_INITIAL_CONTACT,
            message_template=get_template(template_key),
            due_date=now + timedelta(hours=hours),
            template_key=template_key,
            channel=CHANNEL_DM,
        )
        tasks.append(t)
    return tasks


@log_service_action()
def create_proposal_followup_task(
    db: Session, pack_id: UUID, lead_id: UUID | None, lead_name: str
) -> FollowUpTask:
    """Create proposal follow-up task. Per spec: +2 days."""
    due_date = utc_now() + timedelta(days=2)
    return create_followup_task(
        db,
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=TASK_TYPE_PROPOSAL_FOLLOWUP,
        message_template=get_template(TEMPLATE_KEY_PROPOSAL_FOLLOWUP),
        due_date=due_date,
        template_key=TEMPLATE_KEY_PROPOSAL_FOLLOWUP,
        channel=CHANNEL_DM,
    )


@log_service_action()
def create_invoice_followup_task(
    db: Session,
    pack_id: UUID,
    lead_id: UUID | None,
    lead_name: str,
    invoice_due_date: date | None = None,
) -> FollowUpTask:
    """Create invoice chase task. Per spec: +3 days or invoice due_date when present."""
    now = utc_now()
    if invoice_due_date:
        due_date = datetime.combine(
            invoice_due_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
    else:
        due_date = now + timedelta(days=3)
    return create_followup_task(
        db,
        pack_id=pack_id,
        lead_id=lead_id,
        task_type=TASK_TYPE_INVOICE_FOLLOWUP,
        message_template=get_template(TEMPLATE_KEY_INVOICE_CHASE),
        due_date=due_date,
        template_key=TEMPLATE_KEY_INVOICE_CHASE,
        channel=CHANNEL_DM,
    )
