"""Asset model: poster, flyer, video outputs."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pack.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # poster | flyer | video
    version: Mapped[str] = mapped_column(String(16), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)  # display/filename for poster/flyer
    template_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)  # React/TSX code for poster/flyer
    output_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # S3 key
    preview_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # provider temp URL
    preview_image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # S3 key
    script: Mapped[str | None] = mapped_column(String(8000), nullable=True)  # video script
    srt_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # S3 key for subtitles
    sprint_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-7 for 7-day sprint
    chat_messages: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # [{role, content}] for poster/flyer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
