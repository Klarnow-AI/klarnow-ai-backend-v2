"""ORM models for the pack-scoped Docs module."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DOCUMENT_TYPE_PROPOSAL = "proposal"
DOCUMENT_TYPE_INVOICE = "invoice"
DOCUMENT_TYPE_COMPANY_PROFILE = "company_profile"
DOCUMENT_TYPE_MEETING_SUMMARY = "meeting_summary"
DOCUMENT_TYPE_FOLLOW_UP_SUMMARY = "follow_up_summary"
DOCUMENT_TYPE_EMPLOYMENT_LETTER = "employment_letter"
DOCUMENT_TYPE_SPONSORSHIP_LETTER = "sponsorship_letter"
DOCUMENT_TYPES = (
    DOCUMENT_TYPE_PROPOSAL,
    DOCUMENT_TYPE_INVOICE,
    DOCUMENT_TYPE_COMPANY_PROFILE,
    DOCUMENT_TYPE_MEETING_SUMMARY,
    DOCUMENT_TYPE_FOLLOW_UP_SUMMARY,
    DOCUMENT_TYPE_EMPLOYMENT_LETTER,
    DOCUMENT_TYPE_SPONSORSHIP_LETTER,
)

DOCUMENT_STATUS_DRAFT = "draft"
DOCUMENT_STATUS_GENERATED = "generated"
DOCUMENT_STATUS_IN_REVIEW = "in_review"
DOCUMENT_STATUS_READY_TO_SEND = "ready_to_send"
DOCUMENT_STATUS_SENT = "sent"
DOCUMENT_STATUS_ACCEPTED = "accepted"
DOCUMENT_STATUS_PAID = "paid"
DOCUMENT_STATUS_ARCHIVED = "archived"
DOCUMENT_STATUSES = (
    DOCUMENT_STATUS_DRAFT,
    DOCUMENT_STATUS_GENERATED,
    DOCUMENT_STATUS_IN_REVIEW,
    DOCUMENT_STATUS_READY_TO_SEND,
    DOCUMENT_STATUS_SENT,
    DOCUMENT_STATUS_ACCEPTED,
    DOCUMENT_STATUS_PAID,
    DOCUMENT_STATUS_ARCHIVED,
)

DOCUMENT_START_MODE_SUGGESTED = "suggested"
DOCUMENT_START_MODE_TEMPLATE = "template"
DOCUMENT_START_MODE_NOTES = "notes"
DOCUMENT_START_MODES = (
    DOCUMENT_START_MODE_SUGGESTED,
    DOCUMENT_START_MODE_TEMPLATE,
    DOCUMENT_START_MODE_NOTES,
)

TONE_PRESET_FORMAL = "formal"
TONE_PRESET_PROFESSIONAL = "professional"
TONE_PRESET_PERSUASIVE = "persuasive"
TONE_PRESET_CONCISE = "concise"
TONE_PRESET_WARM = "warm"
TONE_PRESETS = (
    TONE_PRESET_FORMAL,
    TONE_PRESET_PROFESSIONAL,
    TONE_PRESET_PERSUASIVE,
    TONE_PRESET_CONCISE,
    TONE_PRESET_WARM,
)


class CompanyData(Base):
    __tablename__ = "company_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    services: Mapped[list | None] = mapped_column(JSON, nullable=True)
    team_members: Mapped[list | None] = mapped_column(JSON, nullable=True)
    packages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    standard_signatory: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    standard_footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    logo_markup: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_voice: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Document(Base):
    __tablename__ = "document"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DOCUMENT_STATUS_DRAFT, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tone_preset: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TONE_PRESET_PROFESSIONAL
    )
    start_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DOCUMENT_START_MODE_TEMPLATE
    )
    inputs_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    export_meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sections: Mapped[list["DocumentSection"]] = relationship(
        "DocumentSection",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSection.order_index",
    )
    linked_document: Mapped["Document | None"] = relationship(
        "Document",
        remote_side="Document.id",
        lazy="joined",
    )


class DocumentSection(Base):
    __tablename__ = "document_section"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(String(128), nullable=False)
    section_label: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    document: Mapped[Document] = relationship("Document", back_populates="sections")
