"""Campaign service: get/set with governance."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.governance import validate_no_revenue_guarantees, validate_one_cta
from app.core.errors import AppError
from app.core.logging import log_service_action
from app.modules.campaign.models import Campaign


@log_service_action()
def get_active_for_pack(db: Session, pack_id: UUID) -> Campaign | None:
    return (
        db.query(Campaign)
        .filter(Campaign.pack_id == pack_id, Campaign.is_active.is_(True))
        .first()
    )


@log_service_action()
def get_by_id_and_pack(db: Session, campaign_id: UUID, pack_id: UUID) -> Campaign | None:
    return (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.pack_id == pack_id)
        .first()
    )


@log_service_action()
def list_versions_for_pack(db: Session, pack_id: UUID) -> list[Campaign]:
    return (
        db.query(Campaign)
        .filter(Campaign.pack_id == pack_id)
        .order_by(Campaign.created_at.desc())
        .all()
    )


def _next_campaign_version(existing: list[Campaign]) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    used = {c.version for c in existing if c.version and len(c.version) == 1 and c.version in letters}
    for c in letters:
        if c not in used:
            return c
    return "Z1"


@log_service_action()
def regenerate_campaign(db: Session, pack_id: UUID, campaign_id: UUID) -> Campaign:
    """Create Version B campaign from existing (copy CTA, goal, angles; never overwrite)."""
    from app.modules.packs.models import Pack

    existing = get_by_id_and_pack(db, campaign_id, pack_id)
    if not existing:
        raise ValueError("Campaign not found")
    existing_list = list_versions_for_pack(db, pack_id)
    version = _next_campaign_version(existing_list)
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise ValueError("Pack not found")
    db.query(Campaign).filter(
        Campaign.pack_id == pack_id,
        Campaign.is_active.is_(True),
    ).update({"is_active": False})
    new_campaign = Campaign(
        pack_id=pack_id,
        version=version,
        primary_cta=existing.primary_cta,
        goal=existing.goal,
        angles=existing.angles or [],
        active_angle_id=existing.active_angle_id,
        is_active=True,
    )
    db.add(new_campaign)
    db.flush()
    pack.active_campaign_id = new_campaign.id
    db.commit()
    db.refresh(new_campaign)
    return new_campaign


@log_service_action()
def create_campaign(
    db: Session,
    pack_id: UUID,
    primary_cta: str,
    goal: dict | None = None,
    angles: list | None = None,
) -> Campaign:
    from app.modules.packs.models import Pack

    validate_one_cta(primary_cta, angles)
    if angles:
        for a in angles:
            if isinstance(a, dict) and a.get("copy"):
                validate_no_revenue_guarantees(str(a.get("copy", "")))
            elif isinstance(a, str):
                validate_no_revenue_guarantees(a)
    campaign = Campaign(
        pack_id=pack_id,
        version="A",
        primary_cta=primary_cta,
        goal=goal,
        angles=angles or [],
        is_active=True,
    )
    db.add(campaign)
    db.flush()
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if pack:
        pack.active_campaign_id = campaign.id
    db.commit()
    db.refresh(campaign)
    return campaign


@log_service_action()
def update_campaign(
    db: Session,
    campaign: Campaign,
    primary_cta: str | None = None,
    goal: dict | None = None,
    angles: list | None = None,
    active_angle_id: str | None = None,
) -> Campaign:
    new_cta = primary_cta if primary_cta is not None else campaign.primary_cta
    new_angles = angles if angles is not None else campaign.angles
    validate_one_cta(new_cta, new_angles)
    if angles is not None:
        for a in angles:
            if isinstance(a, dict) and a.get("copy"):
                validate_no_revenue_guarantees(str(a.get("copy", "")))
            elif isinstance(a, str):
                validate_no_revenue_guarantees(a)
    if primary_cta is not None:
        campaign.primary_cta = primary_cta
    if goal is not None:
        campaign.goal = goal
    if angles is not None:
        campaign.angles = angles
    if active_angle_id is not None:
        campaign.active_angle_id = active_angle_id
    db.commit()
    db.refresh(campaign)
    return campaign
