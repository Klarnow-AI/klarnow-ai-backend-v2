"""Ad Factory persistence models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


COMPILE_STATUS_COMPILED = "compiled"
COMPILE_STATUS_VALIDATION_FAILED = "validation_failed"
COMPILE_STATUS_FAILED = "failed"

RENDER_JOB_STATUS_PENDING = "pending"
RENDER_JOB_STATUS_RESERVED = "reserved"
RENDER_JOB_STATUS_RENDERING = "rendering"
RENDER_JOB_STATUS_COMPLETE = "complete"
RENDER_JOB_STATUS_FAILED = "failed"

RENDER_STATUS_DRAFT = "draft"
RENDER_STATUS_VALIDATED = "validated"
RENDER_STATUS_RENDERING = "rendering"
RENDER_STATUS_COMPLETE = "complete"
RENDER_STATUS_FAILED = "failed"


class AdFactoryCompile(Base):
    __tablename__ = "ad_factory_compile"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=COMPILE_STATUS_COMPILED)
    brand_brief_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pack_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    selection: Mapped[dict] = mapped_column(JSONB, nullable=False)
    versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    compile_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    claim_guard_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validator_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    launch_recommendation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    launch_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class AdFactoryRenderJob(Base):
    __tablename__ = "ad_factory_render_job"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    compile_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_factory_compile.id", ondelete="CASCADE"),
        nullable=False,
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RENDER_JOB_STATUS_PENDING)
    selected_variants: Mapped[list] = mapped_column(JSONB, nullable=False)
    durations_requested: Mapped[list] = mapped_column(JSONB, nullable=False)
    voiceover_addon: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_target: Mapped[str] = mapped_column(String(32), nullable=False, default="kling")
    provider_adapter_version: Mapped[str] = mapped_column(String(64), nullable=False)
    billing_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    provider_job_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    asset_urls: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    retry_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    failure_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    render_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class AdFactoryRender(Base):
    """Legacy table retained for historical rows and temporary compatibility."""

    __tablename__ = "ad_factory_render"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=RENDER_STATUS_DRAFT,
        nullable=False,
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
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
