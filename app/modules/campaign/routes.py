"""Campaign API routes: get/set with governance."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import AppError, NotFoundError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.campaign.schemas import CampaignRead, CampaignUpdate, CampaignCreate
from app.modules.campaign.services import (
    create_campaign,
    get_active_for_pack,
    update_campaign,
    regenerate_campaign,
)

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise NotFoundError("Pack not found")


@router.post("/packs/{pack_id}/campaign", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign_route(
    pack_id: UUID,
    body: CampaignCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create campaign for a pack (one CTA, goal optional). Governance applied."""
    _ensure_pack_access(db, pack_id, current_user.id)
    existing = get_active_for_pack(db, pack_id)
    if existing:
        raise AppError("Pack already has an active campaign; use PATCH to update", status_code=409)
    campaign = create_campaign(
        db,
        pack_id,
        primary_cta=body.primary_cta,
        goal=body.goal.model_dump() if body.goal else None,
        angles=body.angles,
    )
    return CampaignRead.model_validate(campaign)


@router.get("/packs/{pack_id}/campaign", response_model=CampaignRead | None)
def get_campaign(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the active campaign for a pack."""
    _ensure_pack_access(db, pack_id, current_user.id)
    campaign = get_active_for_pack(db, pack_id)
    return CampaignRead.model_validate(campaign) if campaign else None


@router.patch("/packs/{pack_id}/campaign", response_model=CampaignRead)
def update_campaign_route(
    pack_id: UUID,
    body: CampaignUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update campaign (goal, CTA, angles, active angle). Governance: one CTA, no revenue guarantees."""
    _ensure_pack_access(db, pack_id, current_user.id)
    campaign = get_active_for_pack(db, pack_id)
    if not campaign:
        raise NotFoundError("Campaign not found")
    data = body.model_dump(exclude_unset=True)
    goal_dict = data.get("goal")  # already dict from model_dump
    updated = update_campaign(
        db,
        campaign,
        primary_cta=data.get("primary_cta"),
        goal=goal_dict,
        angles=data.get("angles"),
        active_angle_id=data.get("active_angle_id"),
    )
    return CampaignRead.model_validate(updated)


@router.post(
    "/packs/{pack_id}/campaign/{campaign_id}/regenerate",
    response_model=CampaignRead,
    status_code=status.HTTP_201_CREATED,
)
def regenerate_campaign_route(
    pack_id: UUID,
    campaign_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Version B campaign from existing (never overwrite)."""
    _ensure_pack_access(db, pack_id, current_user.id)
    try:
        new_campaign = regenerate_campaign(db, pack_id, campaign_id)
        return CampaignRead.model_validate(new_campaign)
    except ValueError as e:
        raise NotFoundError(str(e))
