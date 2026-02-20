"""Subscription and credits models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PLAN_FREE = "free"
PLAN_STANDARD = "standard"
PLAN_PREMIUM = "premium"
PLANS = (PLAN_FREE, PLAN_STANDARD, PLAN_PREMIUM)

SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_CANCELLED = "cancelled"
SUBSCRIPTION_STATUS_EXPIRED = "expired"
SUBSCRIPTION_STATUSES = (
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CANCELLED,
    SUBSCRIPTION_STATUS_EXPIRED,
)


class Subscription(Base):
    """User subscription with credits."""

    __tablename__ = "subscription"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    plan: Mapped[str] = mapped_column(String(32), default=PLAN_FREE, nullable=False)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credits_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cycle_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cycle_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=SUBSCRIPTION_STATUS_ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
