"""Sprint and DayCard models for 14-day MVP flow."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


SPRINT_STATUS_ACTIVE = "active"
SPRINT_STATUS_COMPLETED = "completed"
SPRINT_STATUSES = (SPRINT_STATUS_ACTIVE, SPRINT_STATUS_COMPLETED)


SPRINT_MODE_BUILD = "build"
SPRINT_MODE_IMPROVE = "improve"
SPRINT_MODES = (SPRINT_MODE_BUILD, SPRINT_MODE_IMPROVE)


class Sprint(Base):
    """14-day sprint per pack. One active sprint per pack at a time."""

    __tablename__ = "sprint"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=SPRINT_STATUS_ACTIVE, nullable=False
    )
    mode: Mapped[str] = mapped_column(
        String(32), default=SPRINT_MODE_BUILD, nullable=False
    )  # build or improve
    current_day: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-14
    success_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # proposals, invoices sent
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    day_cards: Mapped[list["DayCard"]] = relationship(
        "DayCard", back_populates="sprint", cascade="all, delete-orphan", order_by="DayCard.day_number"
    )


class DayCard(Base):
    """Single day (0-14) in a sprint: AI output, user action, definition of done."""

    __tablename__ = "day_card"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sprint.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-14
    ai_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # structured output per day spec
    user_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition_of_done: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Daily completion tracking (Days 4-13)
    outreach_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followup_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    proof_logged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    output_shipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sprint: Mapped["Sprint"] = relationship("Sprint", back_populates="day_cards")
