"""User and Pack models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    packs: Mapped[list["Pack"]] = relationship(
        "Pack", back_populates="created_by_user", cascade="all, delete-orphan"
    )


class EmailLoginCode(Base):
    __tablename__ = "email_login_code"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# Pack type: determines flow (Enquiries / Quotes / Sales). Default enquiries.
PACK_TYPE_ENQUIRIES = "enquiries"
PACK_TYPE_QUOTES = "quotes"
PACK_TYPE_SALES = "sales"
PACK_TYPES = (PACK_TYPE_ENQUIRIES, PACK_TYPE_QUOTES, PACK_TYPE_SALES)


class Pack(Base):
    __tablename__ = "pack"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="draft", nullable=False)  # draft | archived | onboarding
    pack_type: Mapped[str] = mapped_column(
        String(32), default=PACK_TYPE_ENQUIRIES, nullable=False
    )  # enquiries | quotes | sales
    onboarding_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # max 6 questions
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    core_concept: Mapped[str | None] = mapped_column(String(500), nullable=True)  # one sentence everything follows
    active_brand_os_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brand_os.id", ondelete="SET NULL"), nullable=True
    )
    active_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client.id", ondelete="SET NULL"), nullable=True
    )
    # MVP Pack fields (FINAL MVP §9)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    offer_one_liner: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_cta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usp_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    usp_statement: Mapped[str | None] = mapped_column(String(500), nullable=True)
    usp_proof: Mapped[str | None] = mapped_column(String(500), nullable=True)
    usp_locked_line: Mapped[str | None] = mapped_column(String(600), nullable=True)
    proof_types: Mapped[list | None] = mapped_column(JSON, nullable=True)  # array of strings
    proof_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_pain: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_outcome: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hero_angle: Mapped[str | None] = mapped_column(String(64), nullable=True)  # speed | quality | specialist | value
    business_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # product | service | coach
    website_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # for mode detection
    has_existing_customers: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # for mode detection
    day_0_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_user: Mapped["User"] = relationship("User", back_populates="packs")
