"""Pack service: list, create, archive, onboarding."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.packs.models import Pack, PACK_TYPE_ENQUIRIES


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@log_service_action()
def list_packs_for_user(
    db: Session, user_id: UUID, include_archived: bool = False
) -> list[Pack]:
    q = db.query(Pack).filter(Pack.created_by_user_id == user_id)
    if not include_archived:
        q = q.filter(Pack.status != "archived")
    return q.order_by(Pack.created_at.desc()).all()


@log_service_action()
def get_pack_for_user(db: Session, pack_id: UUID, user_id: UUID) -> Pack | None:
    return (
        db.query(Pack)
        .filter(Pack.id == pack_id, Pack.created_by_user_id == user_id)
        .first()
    )


@log_service_action()
def create_pack(
    db: Session,
    user_id: UUID,
    name: str = "New Pack",
    pack_type: str = PACK_TYPE_ENQUIRIES,
) -> Pack:
    pack = Pack(
        name=name,
        status="draft",
        pack_type=pack_type,
        created_by_user_id=user_id,
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    # Start sprint on pack creation day so "Day 0" = when the pack was created
    from app.modules.sprint.services import create_sprint_for_pack
    create_sprint_for_pack(db, pack.id, started_at=pack.created_at)
    return pack


@log_service_action()
def archive_pack(db: Session, pack: Pack) -> Pack:
    pack.status = "archived"
    db.commit()
    db.refresh(pack)
    return pack


@log_service_action()
def restore_pack(db: Session, pack: Pack) -> Pack:
    """Restore an archived pack back to draft status."""
    pack.status = "draft"
    db.commit()
    db.refresh(pack)
    return pack


@log_service_action()
def delete_pack(db: Session, pack: Pack) -> None:
    """Permanently delete a pack and all related data (CASCADE)."""
    db.delete(pack)
    db.commit()


@log_service_action()
def submit_onboarding(db: Session, pack: Pack, answers: dict) -> Pack:
    pack.onboarding_answers = answers
    pack.status = "onboarding"
    db.commit()
    db.refresh(pack)
    return pack


SUGGESTED_LOGOS_MAX = 20


@log_service_action()
def merge_onboarding_answers(db: Session, pack: Pack, partial: dict) -> Pack:
    """Merge partial keys into pack.onboarding_answers and save. Preserves existing keys."""
    current = dict(pack.onboarding_answers or {})
    for k, v in partial.items():
        if v is not None:
            current[k] = v
    pack.onboarding_answers = current
    db.commit()
    db.refresh(pack)
    return pack


def append_suggested_logo(db: Session, pack: Pack, logo_url_or_svg: str) -> Pack:
    """Append a logo URL (or SVG/data URL) to suggested_logos in onboarding_answers, cap at SUGGESTED_LOGOS_MAX."""
    import json
    current = dict(pack.onboarding_answers or {})
    raw = current.get("suggested_logos")
    if isinstance(raw, str):
        try:
            suggested = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            suggested = []
    elif isinstance(raw, list):
        suggested = list(raw)
    else:
        suggested = []
    if not isinstance(suggested, list):
        suggested = []
    suggested.append(logo_url_or_svg)
    current["suggested_logos"] = json.dumps(suggested[-SUGGESTED_LOGOS_MAX:])
    pack.onboarding_answers = current
    db.commit()
    db.refresh(pack)
    return pack


@log_service_action()
def complete_onboarding(db: Session, pack: Pack, answers: dict | None = None) -> Pack:
    pack.onboarding_completed_at = utc_now()
    pack.status = "draft"
    if answers and answers.get("pack_type") in ("enquiries", "quotes", "sales"):
        pack.pack_type = answers["pack_type"]
    db.commit()
    db.refresh(pack)
    return pack
