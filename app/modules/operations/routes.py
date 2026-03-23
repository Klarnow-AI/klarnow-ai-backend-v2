"""Operations API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.operations.schemas import (
    ActionLogEntryList,
    ActionLogEntryRead,
    ActivityCreateResponse,
    ApprovalDecisionBody,
    ApprovalDecisionResponse,
    ApprovalRejectBody,
    ApprovalRequestList,
    ApprovalRequestRead,
    OperatingActivityCreate,
    OperatingActivityList,
    OperatingActivityRead,
    OperationsSummaryRead,
    PackOperatingProfilePatch,
    PackOperatingProfileRead,
    RecommendationFeedbackRead,
)
from app.modules.operations import services
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user


router = APIRouter(prefix="/packs/{pack_id}/operations", tags=["operations"])


def _ensure_pack_access(db: Session, pack_id: UUID, user_id: UUID):
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")
    return pack


@router.get("/profile", response_model=PackOperatingProfileRead)
def get_profile(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    profile = services.get_or_create_operating_profile(db, pack_id)
    return PackOperatingProfileRead.model_validate(profile)


@router.patch("/profile", response_model=PackOperatingProfileRead)
def patch_profile(
    pack_id: UUID,
    body: PackOperatingProfilePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    profile = services.update_operating_profile(
        db, pack_id, **body.model_dump(exclude_unset=True)
    )
    return PackOperatingProfileRead.model_validate(profile)


@router.get("/summary", response_model=OperationsSummaryRead)
def get_summary(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    return OperationsSummaryRead(**services.build_operations_summary(db, pack_id))


@router.get("/activities", response_model=OperatingActivityList)
def list_activities(
    pack_id: UUID,
    status: str | None = Query(None),
    priority: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    items = services.list_activities_for_pack(
        db, pack_id, status=status, priority=priority, limit=limit
    )
    return OperatingActivityList(
        items=[OperatingActivityRead.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("/activities", response_model=ActivityCreateResponse)
def create_activity(
    pack_id: UUID,
    body: OperatingActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    activity, approval = services.create_activity(
        db,
        pack_id=pack_id,
        **body.model_dump(),
    )
    return ActivityCreateResponse(
        activity=OperatingActivityRead.model_validate(activity),
        approval=ApprovalRequestRead.model_validate(approval) if approval else None,
    )


@router.get("/approvals", response_model=ApprovalRequestList)
def list_approvals(
    pack_id: UUID,
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    items = services.list_approvals_for_pack(db, pack_id, status=status, limit=limit)
    return ApprovalRequestList(
        items=[ApprovalRequestRead.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalDecisionResponse)
def approve(
    pack_id: UUID,
    approval_id: UUID,
    body: ApprovalDecisionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    approval, feedback = services.approve_approval_request(
        db,
        pack_id=pack_id,
        approval_id=approval_id,
        decided_by_user_id=current_user.id,
        final_response=body.final_response,
        final_action=body.final_action,
        decision_note=body.decision_note,
    )
    return ApprovalDecisionResponse(
        approval=ApprovalRequestRead.model_validate(approval),
        feedback=RecommendationFeedbackRead.model_validate(feedback),
    )


@router.post("/approvals/{approval_id}/edit-and-approve", response_model=ApprovalDecisionResponse)
def edit_and_approve(
    pack_id: UUID,
    approval_id: UUID,
    body: ApprovalDecisionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    approval, feedback = services.approve_approval_request(
        db,
        pack_id=pack_id,
        approval_id=approval_id,
        decided_by_user_id=current_user.id,
        final_response=body.final_response,
        final_action=body.final_action,
        decision_note=body.decision_note,
    )
    return ApprovalDecisionResponse(
        approval=ApprovalRequestRead.model_validate(approval),
        feedback=RecommendationFeedbackRead.model_validate(feedback),
    )


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalDecisionResponse)
def reject(
    pack_id: UUID,
    approval_id: UUID,
    body: ApprovalRejectBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    approval, feedback = services.reject_approval_request(
        db,
        pack_id=pack_id,
        approval_id=approval_id,
        decided_by_user_id=current_user.id,
        decision_note=body.decision_note,
    )
    return ApprovalDecisionResponse(
        approval=ApprovalRequestRead.model_validate(approval),
        feedback=RecommendationFeedbackRead.model_validate(feedback),
    )


@router.get("/action-log", response_model=ActionLogEntryList)
def list_action_log(
    pack_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_pack_access(db, pack_id, current_user.id)
    items = services.list_action_log_for_pack(db, pack_id, limit=limit)
    return ActionLogEntryList(
        items=[ActionLogEntryRead.model_validate(item) for item in items],
        total=len(items),
    )
