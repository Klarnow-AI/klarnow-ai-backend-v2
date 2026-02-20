"""Conversion page model: React-driven structure, versioned, draft vs published."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversionPage(Base):
    __tablename__ = "conversion_page"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    # React-driven: list of { type, props } sections (e.g. hero, benefits, cta)
    structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Lead filter (required for Day 7 gate)
    lead_filter_type: Mapped[str | None] = mapped_column(String(64), nullable=True)  # starting_price, who_its_for, etc.
    lead_filter_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    proof_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)  # array of Proof IDs
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    seo_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
