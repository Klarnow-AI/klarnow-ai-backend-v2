"""Brand OS model: versioned strategy per pack."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BrandOS(Base):
    __tablename__ = "brand_os"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. "A", "B"
    source_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    foundation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    brand_strategy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
