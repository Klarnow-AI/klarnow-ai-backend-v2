"""Response rules models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


TRIGGER_INITIAL_ENQUIRY = "initial_enquiry"
TRIGGER_PRICE_OBJECTION = "price_objection"
TRIGGER_TIMING_OBJECTION = "timing_objection"
TRIGGER_COMPARISON_OBJECTION = "comparison_objection"
TRIGGER_BOOKING_REQUEST = "booking_request"
TRIGGERS = (
    TRIGGER_INITIAL_ENQUIRY,
    TRIGGER_PRICE_OBJECTION,
    TRIGGER_TIMING_OBJECTION,
    TRIGGER_COMPARISON_OBJECTION,
    TRIGGER_BOOKING_REQUEST,
)


class ResponseRule(Base):
    """Response rule template for common scenarios."""

    __tablename__ = "response_rule"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    response_template: Mapped[str] = mapped_column(Text, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
