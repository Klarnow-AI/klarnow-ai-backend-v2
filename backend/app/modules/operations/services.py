"""Operations services: profile, activity, approvals, action log, and learning."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import log_service_action
from app.modules.clients.models import Lead
from app.modules.operations.models import (
    ACTION_EXECUTION_HUMAN,
    ACTION_EXECUTION_SYSTEM,
    ACTION_MODE_APPROVAL,
    ACTION_MODE_EXTERNAL_DISPATCH,
    ACTION_MODE_NONE,
    ACTION_STATUS_LOGGED,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_REJECTED,
    ACTIVITY_STATUS_OPEN,
    ACTIVITY_STATUS_RESOLVED,
    ACTIVITY_TYPE_BOOKING_REQUEST,
    ACTIVITY_TYPE_CUSTOM_OFFER_REQUEST,
    ACTIVITY_TYPE_DISCOUNT_REQUEST,
    ACTIVITY_TYPE_INVOICE_FOLLOWUP,
    ACTIVITY_TYPE_MANUAL_REVIEW,
    ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP,
    ACTIVITY_TYPE_NEW_LEAD,
    ACTIVITY_TYPE_PAYMENT_TERM_CHANGE,
    ACTIVITY_TYPE_PRICE_CHANGE_REQUEST,
    ACTIVITY_TYPE_QUOTE_REQUEST,
    ACTIVITY_TYPE_REFUND_REQUEST,
    ACTIVITY_TYPE_ROUTINE_QUERY,
    ACTIVITY_TYPE_SERVICE_SCOPE_CHANGE,
    ACTIVITY_TYPE_SUPPORT_ISSUE,
    ApprovalRequest,
    ActionLogEntry,
    COMMERCIAL_SENSITIVITY_REVENUE,
    COMMERCIAL_SENSITIVITY_SAFE,
    CUSTOMER_STAGE_BOOKED,
    CUSTOMER_STAGE_EXISTING,
    CUSTOMER_STAGE_LEAD,
    CUSTOMER_STAGE_SUPPORT,
    FEEDBACK_TYPE_APPROVED,
    FEEDBACK_TYPE_EDITED,
    FEEDBACK_TYPE_REJECTED,
    OperatingActivity,
    PRIORITY_IMPORTANT,
    PRIORITY_LOW,
    PRIORITY_ROUTINE,
    PRIORITY_URGENT,
    PackOperatingProfile,
    RecommendationFeedback,
    RESPONSE_MODE_APPROVAL,
    RESPONSE_MODE_SUGGESTED,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


REVENUE_SENSITIVE_TYPES = {
    ACTIVITY_TYPE_DISCOUNT_REQUEST,
    ACTIVITY_TYPE_REFUND_REQUEST,
    ACTIVITY_TYPE_CUSTOM_OFFER_REQUEST,
    ACTIVITY_TYPE_PRICE_CHANGE_REQUEST,
    ACTIVITY_TYPE_SERVICE_SCOPE_CHANGE,
    ACTIVITY_TYPE_PAYMENT_TERM_CHANGE,
}

DEFAULT_TITLES = {
    ACTIVITY_TYPE_ROUTINE_QUERY: "Routine customer query",
    ACTIVITY_TYPE_NEW_LEAD: "New lead",
    ACTIVITY_TYPE_QUOTE_REQUEST: "Quote request",
    ACTIVITY_TYPE_BOOKING_REQUEST: "Booking request",
    ACTIVITY_TYPE_SUPPORT_ISSUE: "Support issue",
    ACTIVITY_TYPE_DISCOUNT_REQUEST: "Discount request",
    ACTIVITY_TYPE_REFUND_REQUEST: "Refund request",
    ACTIVITY_TYPE_INVOICE_FOLLOWUP: "Invoice follow-up",
    ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP: "Missed lead follow-up",
    ACTIVITY_TYPE_CUSTOM_OFFER_REQUEST: "Custom offer request",
    ACTIVITY_TYPE_PRICE_CHANGE_REQUEST: "Price change request",
    ACTIVITY_TYPE_SERVICE_SCOPE_CHANGE: "Service scope change request",
    ACTIVITY_TYPE_PAYMENT_TERM_CHANGE: "Payment term change request",
    ACTIVITY_TYPE_MANUAL_REVIEW: "Manual review",
}


def _default_customer_stage(activity_type: str) -> str:
    if activity_type in {
        ACTIVITY_TYPE_NEW_LEAD,
        ACTIVITY_TYPE_QUOTE_REQUEST,
        ACTIVITY_TYPE_BOOKING_REQUEST,
        ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP,
    }:
        return CUSTOMER_STAGE_LEAD
    if activity_type in {ACTIVITY_TYPE_REFUND_REQUEST, ACTIVITY_TYPE_INVOICE_FOLLOWUP}:
        return CUSTOMER_STAGE_BOOKED
    if activity_type in {ACTIVITY_TYPE_SUPPORT_ISSUE, ACTIVITY_TYPE_ROUTINE_QUERY}:
        return CUSTOMER_STAGE_SUPPORT
    return CUSTOMER_STAGE_EXISTING


def _default_priority(activity_type: str) -> str:
    if activity_type == ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP:
        return PRIORITY_URGENT
    if activity_type in {
        ACTIVITY_TYPE_NEW_LEAD,
        ACTIVITY_TYPE_QUOTE_REQUEST,
        ACTIVITY_TYPE_DISCOUNT_REQUEST,
        ACTIVITY_TYPE_REFUND_REQUEST,
        ACTIVITY_TYPE_INVOICE_FOLLOWUP,
        ACTIVITY_TYPE_CUSTOM_OFFER_REQUEST,
        ACTIVITY_TYPE_PRICE_CHANGE_REQUEST,
        ACTIVITY_TYPE_SERVICE_SCOPE_CHANGE,
        ACTIVITY_TYPE_PAYMENT_TERM_CHANGE,
    }:
        return PRIORITY_IMPORTANT
    if activity_type == ACTIVITY_TYPE_MANUAL_REVIEW:
        return PRIORITY_LOW
    return PRIORITY_ROUTINE


def _default_reason(activity_type: str) -> str:
    if activity_type in REVENUE_SENSITIVE_TYPES:
        return "Revenue-sensitive request detected. Approval is required before any response or action."
    if activity_type == ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP:
        return "Missed follow-up on a lead was detected and raised to urgent priority."
    if activity_type == ACTIVITY_TYPE_NEW_LEAD:
        return "New lead activity was detected and prioritized for fast follow-up."
    if activity_type == ACTIVITY_TYPE_QUOTE_REQUEST:
        return "Quote request was detected and prioritized because it can directly affect conversion."
    return "Activity was classified using the current operating rules."


def derive_policy_for_activity(activity_type: str, customer_stage: str | None = None) -> dict[str, object]:
    stage = customer_stage or _default_customer_stage(activity_type)
    requires_approval = activity_type in REVENUE_SENSITIVE_TYPES
    commercial_sensitivity = (
        COMMERCIAL_SENSITIVITY_REVENUE if requires_approval else COMMERCIAL_SENSITIVITY_SAFE
    )
    response_mode = RESPONSE_MODE_APPROVAL if requires_approval else RESPONSE_MODE_SUGGESTED
    action_mode = ACTION_MODE_APPROVAL if requires_approval else (
        ACTION_MODE_EXTERNAL_DISPATCH
        if activity_type
        in {
            ACTIVITY_TYPE_ROUTINE_QUERY,
            ACTIVITY_TYPE_NEW_LEAD,
            ACTIVITY_TYPE_QUOTE_REQUEST,
            ACTIVITY_TYPE_BOOKING_REQUEST,
            ACTIVITY_TYPE_SUPPORT_ISSUE,
            ACTIVITY_TYPE_INVOICE_FOLLOWUP,
            ACTIVITY_TYPE_MISSED_LEAD_FOLLOWUP,
        }
        else ACTION_MODE_NONE
    )
    return {
        "customer_stage": stage,
        "priority": _default_priority(activity_type),
        "commercial_sensitivity": commercial_sensitivity,
        "response_mode": response_mode,
        "action_mode": action_mode,
        "requires_approval": requires_approval,
        "detected_reason": _default_reason(activity_type),
    }


def _activity_title(activity_type: str, title: str | None, customer_name: str | None) -> str:
    if title and title.strip():
        return title.strip()
    if customer_name and activity_type == ACTIVITY_TYPE_NEW_LEAD:
        return f"New lead: {customer_name.strip()}"
    return DEFAULT_TITLES.get(activity_type, "Business activity")


def _profile_is_configured(profile: PackOperatingProfile | None) -> bool:
    if not profile:
        return False
    fields = (
        profile.business_type,
        profile.services_offers,
        profile.pricing,
        profile.booking_rules,
        profile.working_hours,
        profile.contact_preferences,
        profile.service_area,
        profile.automation_settings,
        profile.approval_settings,
        profile.business_rules,
        profile.tone_guidance,
        profile.business_notes,
        profile.timezone_name,
    )
    return any(value not in (None, {}, [], "") for value in fields)


def _scenario_key(activity: OperatingActivity, approval: ApprovalRequest | None = None) -> str:
    category = approval.category if approval else "none"
    stage = activity.customer_stage or "unknown"
    return f"{activity.activity_type}:{stage}:{category}"


def _record_action_log(
    db: Session,
    *,
    pack_id: UUID,
    activity_id: UUID | None,
    approval_request_id: UUID | None,
    action_type: str,
    execution_mode: str,
    status: str,
    summary: str | None,
    payload: dict | None = None,
    created_by_user_id: UUID | None = None,
    provider_name: str | None = None,
    provider_ref: str | None = None,
) -> ActionLogEntry:
    entry = ActionLogEntry(
        pack_id=pack_id,
        activity_id=activity_id,
        approval_request_id=approval_request_id,
        action_type=action_type,
        execution_mode=execution_mode,
        status=status,
        summary=summary,
        payload=payload,
        created_by_user_id=created_by_user_id,
        provider_name=provider_name,
        provider_ref=provider_ref,
    )
    db.add(entry)
    return entry


@log_service_action()
def get_or_create_operating_profile(db: Session, pack_id: UUID) -> PackOperatingProfile:
    profile = (
        db.query(PackOperatingProfile)
        .filter(PackOperatingProfile.pack_id == pack_id)
        .first()
    )
    if profile:
        return profile
    profile = PackOperatingProfile(pack_id=pack_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@log_service_action()
def update_operating_profile(db: Session, pack_id: UUID, **updates: object) -> PackOperatingProfile:
    profile = get_or_create_operating_profile(db, pack_id)
    for key, value in updates.items():
        if not hasattr(profile, key):
            continue
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@log_service_action()
def list_activities_for_pack(
    db: Session,
    pack_id: UUID,
    *,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
) -> list[OperatingActivity]:
    q = db.query(OperatingActivity).filter(OperatingActivity.pack_id == pack_id)
    if status:
        q = q.filter(OperatingActivity.status == status)
    if priority:
        q = q.filter(OperatingActivity.priority == priority)
    return q.order_by(OperatingActivity.created_at.desc()).limit(limit).all()


@log_service_action()
def create_activity(
    db: Session,
    *,
    pack_id: UUID,
    activity_type: str,
    title: str | None = None,
    summary: str | None = None,
    customer_name: str | None = None,
    customer_contact: str | None = None,
    customer_stage: str | None = None,
    source_kind: str = "manual",
    source_ref: str | None = None,
    suggested_reply: str | None = None,
    suggested_action: dict | None = None,
    detected_reason: str | None = None,
    payload: dict | None = None,
) -> tuple[OperatingActivity, ApprovalRequest | None]:
    policy = derive_policy_for_activity(activity_type, customer_stage)
    activity = OperatingActivity(
        pack_id=pack_id,
        source_kind=source_kind,
        source_ref=source_ref,
        activity_type=activity_type,
        title=_activity_title(activity_type, title, customer_name),
        summary=summary,
        customer_name=customer_name,
        customer_contact=customer_contact,
        customer_stage=str(policy["customer_stage"]),
        priority=str(policy["priority"]),
        commercial_sensitivity=str(policy["commercial_sensitivity"]),
        status=ACTIVITY_STATUS_OPEN,
        response_mode=str(policy["response_mode"]),
        action_mode=str(policy["action_mode"]),
        requires_approval=bool(policy["requires_approval"]),
        suggested_reply=suggested_reply,
        suggested_action=suggested_action,
        detected_reason=(detected_reason or str(policy["detected_reason"])).strip() or None,
        payload=payload,
    )
    db.add(activity)
    db.flush()

    approval: ApprovalRequest | None = None
    if activity.requires_approval:
        approval = ApprovalRequest(
            pack_id=pack_id,
            activity_id=activity.id,
            category=activity.activity_type,
            status=APPROVAL_STATUS_PENDING,
            reason=activity.detected_reason or _default_reason(activity.activity_type),
            proposed_response=activity.suggested_reply,
            proposed_action=activity.suggested_action,
        )
        db.add(approval)
        db.flush()
        _record_action_log(
            db,
            pack_id=pack_id,
            activity_id=activity.id,
            approval_request_id=approval.id,
            action_type="approval_requested",
            execution_mode=ACTION_EXECUTION_SYSTEM,
            status=ACTION_STATUS_LOGGED,
            summary="Approval request created for revenue-sensitive activity.",
            payload={"category": approval.category},
        )
    elif activity.action_mode == ACTION_MODE_EXTERNAL_DISPATCH and activity.suggested_action:
        _record_action_log(
            db,
            pack_id=pack_id,
            activity_id=activity.id,
            approval_request_id=None,
            action_type="dispatch_prepared",
            execution_mode=ACTION_EXECUTION_SYSTEM,
            status=ACTION_STATUS_LOGGED,
            summary="Dispatch-ready action prepared for external follow-up service.",
            payload=activity.suggested_action,
        )

    db.commit()
    db.refresh(activity)
    if approval:
        db.refresh(approval)
    return activity, approval


@log_service_action()
def publish_new_lead_activity(db: Session, lead: Lead) -> OperatingActivity:
    existing = (
        db.query(OperatingActivity)
        .filter(
            OperatingActivity.pack_id == lead.pack_id,
            OperatingActivity.activity_type == ACTIVITY_TYPE_NEW_LEAD,
            OperatingActivity.source_kind == "lead",
            OperatingActivity.source_ref == str(lead.id),
        )
        .first()
    )
    if existing:
        return existing
    activity, _ = create_activity(
        db,
        pack_id=lead.pack_id,
        activity_type=ACTIVITY_TYPE_NEW_LEAD,
        title=None,
        summary=lead.summary,
        customer_name=lead.name,
        customer_contact=lead.email or lead.phone,
        customer_stage=CUSTOMER_STAGE_LEAD,
        source_kind="lead",
        source_ref=str(lead.id),
        suggested_reply=None,
        suggested_action={
            "kind": "external_followup_dispatch",
            "lead_id": str(lead.id),
            "recommended_next_step": "initial_contact",
        },
        detected_reason="Lead created in Klarnow. Prioritize first response.",
        payload={
            "lead_id": str(lead.id),
            "email": lead.email,
            "phone": lead.phone,
            "source": lead.source,
            "pipeline_stage": lead.pipeline_stage,
        },
    )
    return activity


@log_service_action()
def list_approvals_for_pack(
    db: Session,
    pack_id: UUID,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[ApprovalRequest]:
    q = db.query(ApprovalRequest).filter(ApprovalRequest.pack_id == pack_id)
    if status:
        q = q.filter(ApprovalRequest.status == status)
    return q.order_by(ApprovalRequest.created_at.desc()).limit(limit).all()


@log_service_action()
def get_approval_for_pack(db: Session, pack_id: UUID, approval_id: UUID) -> ApprovalRequest | None:
    return (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.pack_id == pack_id, ApprovalRequest.id == approval_id)
        .first()
    )


def _decision_feedback_type(approval: ApprovalRequest, final_response: str | None, final_action: dict | None) -> str:
    if final_response and final_response != (approval.proposed_response or ""):
        return FEEDBACK_TYPE_EDITED
    if final_action and final_action != (approval.proposed_action or {}):
        return FEEDBACK_TYPE_EDITED
    return FEEDBACK_TYPE_APPROVED


def _create_feedback(
    db: Session,
    *,
    pack_id: UUID,
    activity: OperatingActivity,
    approval: ApprovalRequest,
    feedback_type: str,
    created_by_user_id: UUID | None,
    notes: str | None,
) -> RecommendationFeedback:
    final_content = approval.final_response or approval.proposed_response
    feedback = RecommendationFeedback(
        pack_id=pack_id,
        activity_id=activity.id,
        approval_request_id=approval.id,
        feedback_type=feedback_type,
        scenario_key=_scenario_key(activity, approval),
        original_content=approval.proposed_response,
        final_content=final_content,
        notes=notes,
        created_by_user_id=created_by_user_id,
    )
    db.add(feedback)
    db.flush()
    return feedback


@log_service_action()
def approve_approval_request(
    db: Session,
    *,
    pack_id: UUID,
    approval_id: UUID,
    decided_by_user_id: UUID,
    final_response: str | None = None,
    final_action: dict | None = None,
    decision_note: str | None = None,
) -> tuple[ApprovalRequest, RecommendationFeedback]:
    approval = get_approval_for_pack(db, pack_id, approval_id)
    if not approval:
        raise NotFoundError("Approval request not found")
    if approval.status != APPROVAL_STATUS_PENDING:
        raise ConflictError("Approval request has already been decided")

    activity = db.query(OperatingActivity).filter(OperatingActivity.id == approval.activity_id).first()
    if not activity:
        raise NotFoundError("Activity not found")

    approval.status = APPROVAL_STATUS_APPROVED
    approval.final_response = final_response if final_response is not None else approval.proposed_response
    approval.final_action = final_action if final_action is not None else approval.proposed_action
    approval.decision_note = decision_note
    approval.decided_by_user_id = decided_by_user_id
    approval.decided_at = utc_now()

    activity.status = ACTIVITY_STATUS_RESOLVED
    activity.resolved_at = approval.decided_at

    feedback = _create_feedback(
        db,
        pack_id=pack_id,
        activity=activity,
        approval=approval,
        feedback_type=_decision_feedback_type(approval, final_response, final_action),
        created_by_user_id=decided_by_user_id,
        notes=decision_note,
    )
    _record_action_log(
        db,
        pack_id=pack_id,
        activity_id=activity.id,
        approval_request_id=approval.id,
        action_type="approval_approved",
        execution_mode=ACTION_EXECUTION_HUMAN,
        status=ACTION_STATUS_LOGGED,
        summary="Approval request approved by user.",
        payload={"final_response": approval.final_response, "final_action": approval.final_action},
        created_by_user_id=decided_by_user_id,
    )
    db.commit()
    db.refresh(approval)
    db.refresh(feedback)
    return approval, feedback


@log_service_action()
def reject_approval_request(
    db: Session,
    *,
    pack_id: UUID,
    approval_id: UUID,
    decided_by_user_id: UUID,
    decision_note: str | None = None,
) -> tuple[ApprovalRequest, RecommendationFeedback]:
    approval = get_approval_for_pack(db, pack_id, approval_id)
    if not approval:
        raise NotFoundError("Approval request not found")
    if approval.status != APPROVAL_STATUS_PENDING:
        raise ConflictError("Approval request has already been decided")

    activity = db.query(OperatingActivity).filter(OperatingActivity.id == approval.activity_id).first()
    if not activity:
        raise NotFoundError("Activity not found")

    approval.status = APPROVAL_STATUS_REJECTED
    approval.decision_note = decision_note
    approval.decided_by_user_id = decided_by_user_id
    approval.decided_at = utc_now()

    activity.status = ACTIVITY_STATUS_RESOLVED
    activity.resolved_at = approval.decided_at

    feedback = _create_feedback(
        db,
        pack_id=pack_id,
        activity=activity,
        approval=approval,
        feedback_type=FEEDBACK_TYPE_REJECTED,
        created_by_user_id=decided_by_user_id,
        notes=decision_note,
    )
    _record_action_log(
        db,
        pack_id=pack_id,
        activity_id=activity.id,
        approval_request_id=approval.id,
        action_type="approval_rejected",
        execution_mode=ACTION_EXECUTION_HUMAN,
        status=ACTION_STATUS_LOGGED,
        summary="Approval request rejected by user.",
        payload={"decision_note": decision_note},
        created_by_user_id=decided_by_user_id,
    )
    db.commit()
    db.refresh(approval)
    db.refresh(feedback)
    return approval, feedback


@log_service_action()
def list_action_log_for_pack(db: Session, pack_id: UUID, *, limit: int = 50) -> list[ActionLogEntry]:
    return (
        db.query(ActionLogEntry)
        .filter(ActionLogEntry.pack_id == pack_id)
        .order_by(ActionLogEntry.created_at.desc())
        .limit(limit)
        .all()
    )


@log_service_action()
def build_operations_summary(db: Session, pack_id: UUID) -> dict[str, object]:
    profile = (
        db.query(PackOperatingProfile)
        .filter(PackOperatingProfile.pack_id == pack_id)
        .first()
    )
    open_activities = (
        db.query(OperatingActivity)
        .filter(OperatingActivity.pack_id == pack_id, OperatingActivity.status == ACTIVITY_STATUS_OPEN)
        .all()
    )
    latest_activity = (
        db.query(OperatingActivity)
        .filter(OperatingActivity.pack_id == pack_id)
        .order_by(OperatingActivity.created_at.desc())
        .first()
    )
    pending_approvals = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.pack_id == pack_id, ApprovalRequest.status == APPROVAL_STATUS_PENDING)
        .count()
    )
    action_log_entries = (
        db.query(ActionLogEntry)
        .filter(ActionLogEntry.pack_id == pack_id)
        .count()
    )
    return {
        "profile_configured": _profile_is_configured(profile),
        "open_activities": len(open_activities),
        "urgent_activities": sum(1 for item in open_activities if item.priority == PRIORITY_URGENT),
        "important_activities": sum(1 for item in open_activities if item.priority == PRIORITY_IMPORTANT),
        "pending_approvals": pending_approvals,
        "action_log_entries": action_log_entries,
        "latest_activity_at": latest_activity.created_at if latest_activity else None,
    }
