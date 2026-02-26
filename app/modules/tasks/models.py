"""Follow-up task models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


TASK_TYPE_INITIAL_CONTACT = "initial_contact"
TASK_TYPE_PROPOSAL_FOLLOWUP = "proposal_followup"
TASK_TYPE_INVOICE_FOLLOWUP = "invoice_followup"
TASK_TYPES = (TASK_TYPE_INITIAL_CONTACT, TASK_TYPE_PROPOSAL_FOLLOWUP, TASK_TYPE_INVOICE_FOLLOWUP)

# Template keys per Follow-up MVP spec
TEMPLATE_KEY_FOLLOWUP_2H = "followup_2h"
TEMPLATE_KEY_FOLLOWUP_24H = "followup_24h"
TEMPLATE_KEY_FOLLOWUP_72H = "followup_72h"
TEMPLATE_KEY_PROPOSAL_FOLLOWUP = "proposal_followup"
TEMPLATE_KEY_INVOICE_CHASE = "invoice_chase"

# Channel per spec: dm | whatsapp | call | email
CHANNEL_DM = "dm"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_CALL = "call"
CHANNEL_EMAIL = "email"
CHANNELS = (CHANNEL_DM, CHANNEL_WHATSAPP, CHANNEL_CALL, CHANNEL_EMAIL)

TASK_STATUS_PENDING = "pending"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_SKIPPED = "skipped"
TASK_STATUSES = (TASK_STATUS_PENDING, TASK_STATUS_COMPLETED, TASK_STATUS_SKIPPED)


class FollowUpTask(Base):
    """Follow-up task for leads/proposals/invoices."""

    __tablename__ = "followup_task"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead.id", ondelete="CASCADE"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=TASK_STATUS_PENDING, nullable=False
    )
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)  # dm | whatsapp | call | email
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
