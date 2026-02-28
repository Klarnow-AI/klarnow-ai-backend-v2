"""Day 0-3 readiness: check if all required questions are answered before showing Mark day complete."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack
from app.modules.sprint.day_definitions import get_day_conversation_steps


def _has_value(val: str | None) -> bool:
    return bool(val and str(val).strip())


def is_day_ready_to_complete(db: Session, pack_id: UUID, day_number: int) -> bool:
    """
    Return True if all required questions for the given day (0-3) have been answered.
    Uses pack fields and onboarding_answers.
    """
    if day_number < 0 or day_number > 3:
        return False

    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        return False

    oa = pack.onboarding_answers or {}
    steps = get_day_conversation_steps(day_number)

    # Skip brand_url if has_existing_brand is not "yes"
    has_brand = oa.get("has_existing_brand") == "yes"

    for step in steps:
        key = step.get("key")
        label = step.get("label", "")
        if_has_brand = step.get("if_has_brand", False)

        # Skip optional steps (label contains "optional")
        if "optional" in label.lower():
            continue

        # Skip brand_url when has_existing_brand is not yes
        if if_has_brand and not has_brand:
            continue

        # Check value presence based on field storage
        if key == "has_existing_brand":
            val = oa.get("has_existing_brand")
        elif key == "brand_url":
            val = oa.get("brand_url") or (pack.website_url if pack else None)
        elif key == "brand_name":
            val = pack.brand_name
        elif key == "primary_cta":
            val = pack.primary_cta
        elif key == "usp_category":
            val = pack.usp_category
        elif key == "usp_statement":
            val = pack.usp_statement
        elif key == "offer_one_liner":
            val = pack.offer_one_liner
        elif key == "primary_pain":
            val = pack.primary_pain
        elif key == "primary_outcome":
            val = pack.primary_outcome
        elif key in ("pitch_script", "voice_notes_sent"):
            val = oa.get(key)
        else:
            val = oa.get(key) or getattr(pack, key, None)

        if not _has_value(val):
            return False

    return True
