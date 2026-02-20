"""Sprint service: create 14-day sprint, day cards, completion, reload."""

from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.sprint.models import Sprint, DayCard, SPRINT_STATUS_ACTIVE, SPRINT_STATUS_COMPLETED
from app.modules.sprint.mode_detection import detect_sprint_mode
from app.modules.packs.models import Pack


@log_service_action()
def get_active_sprint_for_pack(db: Session, pack_id: UUID) -> Sprint | None:
    """Return the active sprint for the pack, or None."""
    return (
        db.query(Sprint)
        .filter(Sprint.pack_id == pack_id, Sprint.status == SPRINT_STATUS_ACTIVE)
        .order_by(Sprint.started_at.desc())
        .first()
    )


@log_service_action()
def get_sprint_for_pack(db: Session, pack_id: UUID) -> Sprint | None:
    """Return the active sprint, or the most recent sprint (any status)."""
    return (
        db.query(Sprint)
        .filter(Sprint.pack_id == pack_id)
        .order_by(Sprint.started_at.desc())
        .first()
    )


@log_service_action()
def get_sprint_by_id(db: Session, sprint_id: UUID, pack_id: UUID | None = None) -> Sprint | None:
    """Get sprint by id; optionally ensure it belongs to pack_id."""
    q = db.query(Sprint).filter(Sprint.id == sprint_id)
    if pack_id is not None:
        q = q.filter(Sprint.pack_id == pack_id)
    return q.first()


def _create_day_cards(db: Session, sprint_id: UUID) -> None:
    """Create DayCard rows for day 0 through 14."""
    for day in range(15):
        card = DayCard(sprint_id=sprint_id, day_number=day)
        db.add(card)
    db.flush()


@log_service_action()
def create_sprint_for_pack(db: Session, pack_id: UUID, started_at: datetime | None = None) -> Sprint:
    """Create a new 14-day sprint for the pack with DayCards 0-14. Fails if pack already has an active sprint.
    If started_at is provided (e.g. pack.created_at), the sprint is anchored to that date; otherwise uses now."""
    existing = get_active_sprint_for_pack(db, pack_id)
    if existing:
        raise ValueError("Pack already has an active sprint. Complete Day 14 check-in first.")
    
    # Get pack and detect mode
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise ValueError(f"Pack {pack_id} not found")
    
    mode = detect_sprint_mode(pack, db)
    sprint_start = started_at if started_at is not None else datetime.now(timezone.utc)
    
    sprint = Sprint(
        pack_id=pack_id,
        status=SPRINT_STATUS_ACTIVE,
        current_day=0,
        mode=mode,
        started_at=sprint_start,
    )
    db.add(sprint)
    db.flush()
    _create_day_cards(db, sprint.id)
    db.commit()
    db.refresh(sprint)
    return sprint


@log_service_action()
def get_day_card(db: Session, sprint_id: UUID, day_number: int) -> DayCard | None:
    """Get the day card for a given day (0-14)."""
    if day_number < 0 or day_number > 14:
        return None
    return (
        db.query(DayCard)
        .filter(DayCard.sprint_id == sprint_id, DayCard.day_number == day_number)
        .first()
    )


@log_service_action()
def update_day_card(
    db: Session,
    card: DayCard,
    ai_output: dict | None = None,
    user_action: str | None = None,
    definition_of_done: str | None = None,
    completed_at: datetime | None = None,
) -> DayCard:
    """Update a day card's content and/or completion."""
    if ai_output is not None:
        card.ai_output = ai_output
    if user_action is not None:
        card.user_action = user_action
    if definition_of_done is not None:
        card.definition_of_done = definition_of_done
    if completed_at is not None:
        card.completed_at = completed_at
    db.commit()
    db.refresh(card)
    return card


@log_service_action()
def complete_day(db: Session, sprint: Sprint, day_number: int, user_selections: dict | None = None) -> Sprint:
    """
    Mark a day card as completed and advance sprint current_day.
    For Day 1 & 2, sync selected values to Pack fields.
    
    Args:
        db: Database session
        sprint: Sprint to update
        day_number: Day number (0-14)
        user_selections: Optional dict (Day 1: offer_one_liner; Day 2: primary_pain, primary_outcome)
    """
    from app.core.gates import can_complete_day
    
    card = get_day_card(db, sprint.id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")
    
    if card.completed_at is not None:
        return sprint
    
    # Get pack for gate check
    pack = db.query(Pack).filter(Pack.id == sprint.pack_id).first()
    if not pack:
        raise ValueError(f"Pack {sprint.pack_id} not found")
    
    # Check daily completion gate (Days 4-13)
    can_pass, blocker_msg = can_complete_day(db, card, day_number, pack)
    if not can_pass:
        raise ValueError(blocker_msg)
    
    now = datetime.now(timezone.utc)
    card.completed_at = now
    sprint.current_day = max(sprint.current_day, day_number + 1)
    
    if day_number == 14:
        sprint.status = SPRINT_STATUS_COMPLETED
        sprint.completed_at = now
    
    # Sync Pack fields for Day 1 & 2
    if user_selections and day_number in (1, 2):
        if day_number == 1:
            # Day 1: Offer
            if "offer_one_liner" in user_selections:
                pack.offer_one_liner = (user_selections["offer_one_liner"] or "").strip() or None
        elif day_number == 2:
            # Day 2: USP + Audience - set pain and outcome
            if "primary_pain" in user_selections:
                pack.primary_pain = user_selections["primary_pain"]
            if "primary_outcome" in user_selections:
                pack.primary_outcome = user_selections["primary_outcome"]
    
    db.commit()
    db.refresh(sprint)
    return sprint


@log_service_action()
def complete_sprint_and_reload(db: Session, pack_id: UUID, sprint_id: UUID) -> Sprint:
    """
    Complete the given sprint (Day 14 check-in) and create Sprint 2 automatically.
    Returns the new active sprint.
    """
    sprint = get_sprint_by_id(db, sprint_id, pack_id=pack_id)
    if not sprint:
        raise ValueError("Sprint not found")
    if sprint.status == SPRINT_STATUS_COMPLETED:
        raise ValueError("Sprint already completed")
    # Mark day 14 complete and this sprint completed
    complete_day(db, sprint, 14)
    # Create next sprint
    new_sprint = create_sprint_for_pack(db, pack_id)
    return new_sprint


@log_service_action()
def get_sprint_day_detail(db: Session, pack_id: UUID, day_number: int) -> dict | None:
    """
    Return detail for one day (0-14) of the pack's active sprint.
    Days beyond current_day are locked. Day 7/8 check specific gates.
    """
    if day_number < 0 or day_number > 14:
        return None
    sprint = get_active_sprint_for_pack(db, pack_id)
    if not sprint:
        return None
    card = get_day_card(db, sprint.id, day_number)
    if not card:
        return None

    from app.modules.sprint.outreach_targets import get_daily_outreach_target, get_daily_followup_target
    pack = db.query(Pack).filter(Pack.id == sprint.pack_id).first()
    business_type = (pack.business_type if pack else None) or "product"
    outreach_target = get_daily_outreach_target(business_type)
    followup_target = get_daily_followup_target(business_type)

    unlocked = day_number <= sprint.current_day
    blocker_message: str | None = None

    if unlocked and pack:
        from app.core.gates import can_pass_day7_gate, can_pass_day8_gate
        if day_number == 7:
            ok, msg = can_pass_day7_gate(db, pack)
            if not ok:
                unlocked = False
                blocker_message = msg
        elif day_number == 8:
            ok, msg = can_pass_day8_gate(db, pack)
            if not ok:
                unlocked = False
                blocker_message = msg

    if not unlocked and not blocker_message:
        blocker_message = f"Complete Day {day_number - 1} first to unlock this day."

    return {
        "day_number": day_number,
        "title": f"Day {day_number}",
        "ai_output": card.ai_output,
        "user_action": card.user_action,
        "definition_of_done": card.definition_of_done,
        "completed_at": card.completed_at,
        "unlocked": unlocked,
        "blocker_message": blocker_message if not unlocked else None,
        "outreach_count": card.outreach_count,
        "followup_count": card.followup_count,
        "proof_logged": card.proof_logged,
        "output_shipped": card.output_shipped,
        "outreach_target": outreach_target,
        "followup_target": followup_target,
    }


@log_service_action()
def log_outreach(db: Session, sprint_id: UUID, day_number: int, count: int = 1) -> DayCard:
    """Log outreach activities for a sprint day."""
    card = get_day_card(db, sprint_id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")
    
    card.outreach_count += count
    db.commit()
    db.refresh(card)
    return card


@log_service_action()
def log_followup(db: Session, sprint_id: UUID, day_number: int, count: int = 1) -> DayCard:
    """Log follow-up activities for a sprint day."""
    card = get_day_card(db, sprint_id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")
    
    card.followup_count += count
    db.commit()
    db.refresh(card)
    return card


@log_service_action()
def mark_proof_logged(db: Session, sprint_id: UUID, day_number: int) -> DayCard:
    """Mark proof as logged for a sprint day."""
    card = get_day_card(db, sprint_id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")
    
    card.proof_logged = True
    db.commit()
    db.refresh(card)
    return card


@log_service_action()
def mark_output_shipped(db: Session, sprint_id: UUID, day_number: int) -> DayCard:
    """Mark output as shipped for a sprint day."""
    card = get_day_card(db, sprint_id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")
    
    card.output_shipped = True
    db.commit()
    db.refresh(card)
    return card

