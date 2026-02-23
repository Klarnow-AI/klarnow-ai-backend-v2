"""Proposal and Invoice models."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Proposal(Base):
    __tablename__ = "proposal"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft | sent | accepted | declined
    amount: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "1500.00"
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # free-form summary/items
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Invoice(Base):
    __tablename__ = "invoice"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft | sent | paid | overdue
    amount: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    # Stripe: when invoice is published for payment, store Stripe invoice id and hosted URL
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_hosted_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
