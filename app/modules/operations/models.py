"""Operating intelligence data models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ACTIVITY_TYPE_ROUTINE_QUERY = "routine_query"
ACTIVITY_TYPE_NEW_LEAD = "new_lead"
ACTIVITY_TYPE_QUOTE_REQUEST = "quote_request"
ACTIVITY_TYPE_BOOKING_REQUEST = "booking_request"
ACTIVITY_TYPE_SUPPORT_ISSUE = "support_issue"
ACTIVITY_TYPE_DISCOUNT_REQUEST = "discount_request"
ACTIVITY_TYPE_REFUND_REQUEST = "refund_request"
ACTIVITY_TYPE_INVOICE_FOLLOWUP = "invoice_followup"
ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP = "missed_lead_followup"
ACTIVITY_TYPE_CUSTOM_OFFER_REQUEST = "custom_offer_request"
ACTIVITY_TYPE_PRICE_CHANGE_REQUEST = "price_change_request"
ACTIVITY_TYPE_SERVICE_SCOPE_CHANGE = "service_scope_change"
ACTIVITY_TYPE_PAYMENT_TERM_CHANGE = "payment_term_change"
ACTIVITY_TYPE_MANUAL_REVIEW = "manual_review"

PRIORITY_URGENT = "urgent"
PRIORITY_IMPORTANT = "important"
PRIORITY_ROUTINE = "routine"
PRIORITY_LOW = "low_priority"

CUSTOMER_STAGE_LEAD = "lead"
CUSTOMER_STAGE_BOOKED = "booked_customer"
CUSTOMER_STAGE_SUPPORT = "support_query"
CUSTOMER_STAGE_EXISTING = "existing_customer"

COMMERCIAL_SENSITIVITY_SAFE = "safe"
COMMERCIAL_SENSITIVITY_REVENUE = "revenue_sensitive"

ACTIVITY_STATUS_OPEN = "open"
ACTIVITY_STATUS_IN_PROGRESS = "in_progress"
ACTIVITY_STATUS_RESOLVED = "resolved"
ACTIVITY_STATUS_DISMISSED = "dismissed"

RESPONSE_MODE_AUTO = "auto_reply"
RESPONSE_MODE_SUGGESTED = "suggested_reply"
RESPONSE_MODE_APPROVAL = "approval_required"

ACTION_MODE_NONE = "none"
ACTION_MODE_EXTERNAL_DISPATCH = "external_dispatch"
ACTION_MODE_INTERNAL_UPDATE = "internal_update"
ACTION_MODE_APPROVAL = "approval_required"

APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"

ACTION_EXECUTION_SYSTEM = "system"
ACTION_EXECUTION_HUMAN = "human"
ACTION_EXECUTION_EXTERNAL = "external_service"

ACTION_STATUS_LOGGED = "logged"
ACTION_STATUS_QUEUED = "queued"
ACTION_STATUS_EXECUTED = "executed"
ACTION_STATUS_REJECTED = "rejected"
ACTION_STATUS_FAILED = "failed"

FEEDBACK_TYPE_APPROVED = "approved"
FEEDBACK_TYPE_REJECTED = "rejected"
FEEDBACK_TYPE_EDITED = "edited"


class PackOperatingProfile(Base):
    __tablename__ = "pack_operating_profile"

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
    business_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    services_offers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pricing: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    booking_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    working_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contact_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    service_area: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    automation_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    business_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tone_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class OperatingActivity(Base):
    __tablename__ = "operating_activity"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_kind: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str] = mapped_column(String(32), default=PRIORITY_ROUTINE, nullable=False, index=True)
    commercial_sensitivity: Mapped[str] = mapped_column(
        String(64), default=COMMERCIAL_SENSITIVITY_SAFE, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=ACTIVITY_STATUS_OPEN, nullable=False, index=True)
    response_mode: Mapped[str] = mapped_column(String(64), default=RESPONSE_MODE_SUGGESTED, nullable=False)
    action_mode: Mapped[str] = mapped_column(String(64), default=ACTION_MODE_NONE, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    detected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalRequest(Base):
    __tablename__ = "approval_request"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operating_activity.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=APPROVAL_STATUS_PENDING, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ActionLogEntry(Base):
    __tablename__ = "action_log_entry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operating_activity.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_request.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pack.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operating_activity.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_request.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

