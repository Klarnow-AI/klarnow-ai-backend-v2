"""Ad Factory V2 models: AdFactoryRender stores full render contract."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


RENDER_STATUS_DRAFT = "draft"
RENDER_STATUS_VALIDATED = "validated"
RENDER_STATUS_RENDERING = "rendering"
RENDER_STATUS_COMPLETE = "complete"
RENDER_STATUS_FAILED = "failed"


class AdFactoryRender(Base):
    __tablename__ = "ad_factory_render"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=RENDER_STATUS_DRAFT, nullable=False
    )
    brand_brief_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pack_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    selection_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    pattern_ids_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hook_ids_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    proof_strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engines_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    variants: Mapped[dict] = mapped_column(JSONB, nullable=False)
    render_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
