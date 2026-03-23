"""Sprint tools for Day 0-3 conversational flow."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import DomainGateBlockedError, DomainNotFoundError
from app.modules.sprint.services import get_active_sprint_for_pack, complete_day


COMPLETE_SPRINT_DAY_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "day_number": {
            "type": "integer",
            "minimum": 0,
            "maximum": 3,
            "description": "Day to complete (0-3)",
        },
        "user_selections": {
            "type": "object",
            "description": "Day 1: offer_one_liner; Day 2: primary_pain, primary_outcome, target_audience; Day 3: pitch_script, voice_notes_sent",
            "additionalProperties": True,
        },
    },
    "required": ["pack_id", "day_number"],
}


def complete_sprint_day(
    db: Session,
    pack_id: UUID,
    day_number: int,
    user_selections: dict | None = None,
) -> dict:
    """
    Mark a sprint day (0-3) as complete and advance current_day.
    For Day 1 & 2, user_selections are synced to Pack.
    Day 0: ensure pack.day_0_completed_at is set before calling (use update_pack first).
    """
    if isinstance(pack_id, str):
        pack_id = UUID(pack_id)
    sprint = get_active_sprint_for_pack(db, pack_id)
    if not sprint:
        raise DomainNotFoundError("No active sprint for this pack. Start a sprint from the plan tracker.")

    if day_number < 0 or day_number > 3:
        raise ValueError("day_number must be 0, 1, 2, or 3 for this flow")

    sprint = complete_day(db, sprint, day_number, user_selections)
    return {
        "completed": True,
        "day_number": day_number,
        "current_day": sprint.current_day,
    }
