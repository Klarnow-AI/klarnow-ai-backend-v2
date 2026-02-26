"""Client and Lead models. Client owned by user; Lead scoped to pack."""

import uuid
from datetime import datetime, timezone

from datetime import date

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Lead status for mini CRM pipeline
LEAD_STATUS_NEW = "new"
LEAD_STATUS_CONTACTED = "contacted"
LEAD_STATUS_QUALIFIED = "qualified"
LEAD_STATUS_DISQUALIFIED = "disqualified"
LEAD_STATUS_CONVERTED = "converted"
LEAD_STATUSES = (
    LEAD_STATUS_NEW,
    LEAD_STATUS_CONTACTED,
    LEAD_STATUS_QUALIFIED,
    LEAD_STATUS_DISQUALIFIED,
    LEAD_STATUS_CONVERTED,
)

# Pipeline stages for Kanban columns
PIPELINE_STAGE_CONTACTED = "contacted"
PIPELINE_STAGE_DRAFTING = "drafting"
PIPELINE_STAGE_PROPOSAL = "proposal"
PIPELINE_STAGE_CLOSED = "closed"
PIPELINE_STAGES = (
    PIPELINE_STAGE_CONTACTED,
    PIPELINE_STAGE_DRAFTING,
    PIPELINE_STAGE_PROPOSAL,
    PIPELINE_STAGE_CLOSED,
)


class Client(Base):
    __tablename__ = "client"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Lead(Base):
    __tablename__ = "lead"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=LEAD_STATUS_NEW, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_range: Mapped[str | None] = mapped_column(String(128), nullable=True)  # Quotes pack
    urgency: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Quotes pack
    pipeline_stage: Mapped[str] = mapped_column(
        String(32), default=PIPELINE_STAGE_CONTACTED, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deal_value: Mapped[str | None] = mapped_column(Numeric(14, 2), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
