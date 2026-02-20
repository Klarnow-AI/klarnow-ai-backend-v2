"""Brand OS service: read-only access and update active."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.brand_os.domain_schema import BrandFoundation, BrandStrategyProfile
from app.modules.brand_os.models import BrandOS


def get_summary_fields(brand_os: BrandOS) -> tuple[str | None, str | None, bool]:
    """Derive (mission, vision, has_positioning) for pack summary from brand_strategy."""
    if not brand_os.brand_strategy or not isinstance(brand_os.brand_strategy, dict):
        return (None, None, False)
    bs = brand_os.brand_strategy
    mv = bs.get("mission_vision") or {}
    mission = mv.get("mission")
    vision = mv.get("vision")
    pos = bs.get("positioning_differentiation") or {}
    has_positioning = bool(pos.get("statement") or pos.get("unique_advantage"))
    return (mission, vision, has_positioning)


def get_context_strings(brand_os: BrandOS) -> tuple[str | None, str | None, str, str]:
    """(mission, vision, values_or_purpose_str, voice_str) for downstream tools from foundation/brand_strategy."""
    if not brand_os.brand_strategy or not isinstance(brand_os.brand_strategy, dict):
        return (None, None, "", "")
    bs = brand_os.brand_strategy
    mv = bs.get("mission_vision") or {}
    mission = mv.get("mission")
    vision = mv.get("vision")
    vp = brand_os.foundation if isinstance(brand_os.foundation, dict) else {}
    purpose = vp.get("brand_purpose") or []
    values_str = ", ".join(purpose) if isinstance(purpose, list) else str(purpose)
    voice = bs.get("voice_personality") or {}
    archetype = voice.get("archetype") or ""
    profile = voice.get("profile") or []
    voice_str = f"Archetype: {archetype}. Profile: {', '.join(profile) if isinstance(profile, list) else str(profile)}"
    return (mission, vision, values_str, voice_str)


@log_service_action()
def get_active_for_pack(db: Session, pack_id: UUID) -> BrandOS | None:
    return (
        db.query(BrandOS)
        .filter(BrandOS.pack_id == pack_id, BrandOS.is_active.is_(True))
        .first()
    )


@log_service_action()
def list_versions_for_pack(db: Session, pack_id: UUID) -> list[BrandOS]:
    return (
        db.query(BrandOS)
        .filter(BrandOS.pack_id == pack_id)
        .order_by(BrandOS.created_at.desc())
        .all()
    )


@log_service_action()
def get_by_id_and_pack(db: Session, brand_os_id: UUID, pack_id: UUID) -> BrandOS | None:
    return (
        db.query(BrandOS)
        .filter(BrandOS.id == brand_os_id, BrandOS.pack_id == pack_id)
        .first()
    )


@log_service_action()
def get_by_version_and_pack(db: Session, pack_id: UUID, version: str) -> BrandOS | None:
    return (
        db.query(BrandOS)
        .filter(BrandOS.pack_id == pack_id, BrandOS.version == version)
        .first()
    )


@log_service_action()
def update_active_brand_os(
    db: Session,
    pack_id: UUID,
    *,
    foundation: BrandFoundation | None = None,
    brand_strategy: BrandStrategyProfile | None = None,
) -> BrandOS | None:
    """Update the active Brand OS for the pack. Merges provided foundation/brand_strategy (full replace per key). Returns updated row or None if no active."""
    row = get_active_for_pack(db, pack_id)
    if not row:
        return None
    if foundation is not None:
        row.foundation = foundation.model_dump()
    if brand_strategy is not None:
        row.brand_strategy = brand_strategy.model_dump()
    db.commit()
    db.refresh(row)
    return row
