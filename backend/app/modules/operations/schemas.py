"""Operations API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PackOperatingProfilePatch(BaseModel):
    business_type: str | None = None
    services_offers: dict[str, Any] | None = None
    pricing: dict[str, Any] | None = None
    booking_rules: dict[str, Any] | None = None
    working_hours: dict[str, Any] | None = None
    contact_preferences: dict[str, Any] | None = None
    service_area: dict[str, Any] | None = None
    automation_settings: dict[str, Any] | None = None
    approval_settings: dict[str, Any] | None = None
    business_rules: dict[str, Any] | None = None
    tone_guidance: str | None = None
    business_notes: str | None = None
    timezone_name: str | None = None

    model_config = {"extra": "forbid"}


class PackOperatingProfileRead(BaseModel):
    id: UUID
    pack_id: UUID
    business_type: str | None
    services_offers: dict[str, Any] | None
    pricing: dict[str, Any] | None
    booking_rules: dict[str, Any] | None
    working_hours: dict[str, Any] | None
    contact_preferences: dict[str, Any] | None
    service_area: dict[str, Any] | None
    automation_settings: dict[str, Any] | None
    approval_settings: dict[str, Any] | None
    business_rules: dict[str, Any] | None
    tone_guidance: str | None
    business_notes: str | None
    timezone_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OperatingActivityCreate(BaseModel):
    activity_type: str
    title: str | None = None
    summary: str | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    customer_stage: str | None = None
    source_kind: str = "manual"
    source_ref: str | None = None
    suggested_reply: str | None = None
    suggested_action: dict[str, Any] | None = None
    detected_reason: str | None = None
    payload: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class OperatingActivityRead(BaseModel):
    id: UUID
    pack_id: UUID
    source_kind: str
    source_ref: str | None
    activity_type: str
    title: str | None
    summary: str | None
    customer_name: str | None
    customer_contact: str | None
    customer_stage: str | None
    priority: str
    commercial_sensitivity: str
    status: str
    response_mode: str
    action_mode: str
    requires_approval: bool
    suggested_reply: str | None
    suggested_action: dict[str, Any] | None
    detected_reason: str | None
    payload: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class ApprovalDecisionBody(BaseModel):
    final_response: str | None = None
    final_action: dict[str, Any] | None = None
    decision_note: str | None = None

    model_config = {"extra": "forbid"}


class ApprovalRejectBody(BaseModel):
    decision_note: str | None = None

    model_config = {"extra": "forbid"}


class ApprovalRequestRead(BaseModel):
    id: UUID
    pack_id: UUID
    activity_id: UUID
    category: str
    status: str
    reason: str
    proposed_response: str | None
    proposed_action: dict[str, Any] | None
    final_response: str | None
    final_action: dict[str, Any] | None
    decision_note: str | None
    decided_by_user_id: UUID | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActionLogEntryRead(BaseModel):
    id: UUID
    pack_id: UUID
    activity_id: UUID | None
    approval_request_id: UUID | None
    action_type: str
    execution_mode: str
    status: str
    summary: str | None
    provider_name: str | None
    provider_ref: str | None
    payload: dict[str, Any] | None
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationFeedbackRead(BaseModel):
    id: UUID
    pack_id: UUID
    activity_id: UUID | None
    approval_request_id: UUID | None
    feedback_type: str
    scenario_key: str
    original_content: str | None
    final_content: str | None
    notes: str | None
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationsSummaryRead(BaseModel):
    profile_configured: bool
    open_activities: int
    urgent_activities: int
    important_activities: int
    pending_approvals: int
    action_log_entries: int
    latest_activity_at: datetime | None = None


class ActivityCreateResponse(BaseModel):
    activity: OperatingActivityRead
    approval: ApprovalRequestRead | None = None


class ApprovalDecisionResponse(BaseModel):
    approval: ApprovalRequestRead
    feedback: RecommendationFeedbackRead


class OperatingActivityList(BaseModel):
    items: list[OperatingActivityRead]
    total: int


class ApprovalRequestList(BaseModel):
    items: list[ApprovalRequestRead]
    total: int


class ActionLogEntryList(BaseModel):
    items: list[ActionLogEntryRead]
    total: int

