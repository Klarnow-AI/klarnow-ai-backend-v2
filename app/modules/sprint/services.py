"""Sprint service: create 14-day sprint, day cards, completion, reload."""

import json
import re
from uuid import UUID
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger, log_service_action
from app.modules.sprint.models import Sprint, DayCard, SPRINT_STATUS_ACTIVE, SPRINT_STATUS_COMPLETED
from app.modules.sprint.mode_detection import detect_sprint_mode
from app.modules.sprint.day_definitions import get_day_content, get_day_definition
from app.modules.packs.models import Pack

logger = get_logger()

TODAY_TASKS_CACHE_KEY = "overview_today_tasks_v1"
TODAY_TASKS_MIN_COUNT = 3
TODAY_TASKS_MAX_COUNT = 5


class StaleDayError(ValueError):
    """Raised when a checklist update targets an outdated sprint day."""


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.startswith("json"):
        text = text[4:].lstrip()
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0].strip()
    return text


def _slug_task_id(label: str, existing: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "task"
    candidate = base
    i = 2
    while candidate in existing:
        candidate = f"{base}-{i}"
        i += 1
    existing.add(candidate)
    return candidate


def _normalise_labels(labels: list[str], max_count: int = TODAY_TASKS_MAX_COUNT) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in labels:
        if not isinstance(raw, str):
            continue
        compact = " ".join(raw.strip().split())
        if not compact:
            continue
        key = compact.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(compact)
        if len(out) >= max_count:
            break
    return out


def _build_task_items(labels: list[str]) -> list[dict[str, Any]]:
    used_ids: set[str] = set()
    return [
        {"id": _slug_task_id(label, used_ids), "label": label, "checked": False}
        for label in labels
    ]


def _normalise_cached_tasks(raw_tasks: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_tasks, list):
        return []

    out: list[dict[str, Any]] = []
    used: set[str] = set()
    for task in raw_tasks:
        if not isinstance(task, dict):
            continue
        label = " ".join(str(task.get("label") or "").strip().split())
        if not label:
            continue
        task_id = str(task.get("id") or "").strip() or _slug_task_id(label, used)
        if task_id in used:
            task_id = _slug_task_id(task_id, used)
        else:
            used.add(task_id)
        out.append(
            {
                "id": task_id,
                "label": label,
                "checked": bool(task.get("checked")),
            }
        )
    return out[:TODAY_TASKS_MAX_COUNT]


def _get_cached_today_tasks(card: DayCard, day_number: int) -> dict[str, Any] | None:
    if not isinstance(card.ai_output, dict):
        return None

    cache = card.ai_output.get(TODAY_TASKS_CACHE_KEY)
    if not isinstance(cache, dict):
        return None
    if cache.get("day_number") != day_number:
        return None

    tasks = _normalise_cached_tasks(cache.get("tasks"))
    if not tasks:
        return None
    return {
        "day_number": day_number,
        "source": str(cache.get("source") or "fallback"),
        "generated_at": cache.get("generated_at"),
        "tasks": tasks,
    }


def _pack_context_for_today_tasks(pack: Pack) -> str:
    context_parts: list[str] = []
    if pack.brand_name:
        context_parts.append(f"Brand name: {pack.brand_name}")
    if pack.primary_cta:
        context_parts.append(f"Primary CTA: {pack.primary_cta}")
    if pack.usp_statement:
        context_parts.append(f"USP: {pack.usp_statement}")
    if pack.offer_one_liner:
        context_parts.append(f"Offer: {pack.offer_one_liner}")
    if pack.target_audience:
        context_parts.append(f"Audience: {pack.target_audience}")
    if pack.primary_pain:
        context_parts.append(f"Primary pain: {pack.primary_pain}")
    if pack.primary_outcome:
        context_parts.append(f"Primary outcome: {pack.primary_outcome}")
    if pack.hero_angle:
        context_parts.append(f"Hero angle: {pack.hero_angle}")

    oa = pack.onboarding_answers or {}
    if isinstance(oa, str):
        try:
            oa = json.loads(oa) if oa else {}
        except Exception:
            oa = {}
    if isinstance(oa, dict):
        for key in ("brand_url", "usp_proof", "proof_text"):
            val = oa.get(key)
            if isinstance(val, str) and val.strip():
                context_parts.append(f"{key}: {val.strip()[:280]}")

    return "\n".join(context_parts) if context_parts else "No pack context available yet."


def _fallback_task_labels(day_number: int, mode: str) -> tuple[list[str], str]:
    day_content = get_day_content(day_number, mode)
    labels = _normalise_labels(list(day_content.get("tasks") or []))
    if len(labels) >= TODAY_TASKS_MIN_COUNT:
        return labels, day_content.get("playbook") or ""

    day_def = get_day_definition(day_number)
    fill: list[str] = []
    if day_def.get("win_condition"):
        fill.append(f"Hit the win condition: {day_def['win_condition']}")
    if day_content.get("playbook"):
        fill.append("Review the day playbook and execute one concrete step")
    labels = _normalise_labels(labels + fill)
    return labels, day_content.get("playbook") or ""


def _generate_today_task_labels_with_llm(
    *,
    day_number: int,
    day_title: str,
    mode: str,
    overview: str,
    fallback_labels: list[str],
    pack_context: str,
) -> list[str] | None:
    settings = get_settings()
    if not settings.openai_api_key or not settings.ai_sprint_today_tasks_enabled:
        return None

    prompt = (
        "You are generating checklist tasks for a single sprint day in a business execution app.\n"
        "Return ONLY JSON: {\"tasks\":[\"...\",\"...\",\"...\"]}.\n"
        f"Rules:\n"
        f"- exactly {TODAY_TASKS_MIN_COUNT} to {TODAY_TASKS_MAX_COUNT} tasks\n"
        "- each task <= 70 characters\n"
        "- imperative, concrete, non-generic\n"
        "- no numbering, no punctuation at end\n"
        "- align to today only\n\n"
        f"Day number: {day_number}\n"
        f"Day title: {day_title}\n"
        f"Sprint mode: {mode}\n"
        f"Day overview: {overview}\n"
        f"Fallback tasks: {json.dumps(fallback_labels, ensure_ascii=True)}\n"
        f"Pack context:\n{pack_context}\n"
    )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You output strict JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        raw = response.choices[0].message.content if response.choices else ""
        if not raw:
            return None
        parsed = json.loads(_strip_markdown_fences(raw))
        labels = parsed.get("tasks") if isinstance(parsed, dict) else None
        if not isinstance(labels, list):
            return None
        cleaned = _normalise_labels(labels)
        if len(cleaned) < TODAY_TASKS_MIN_COUNT:
            return None
        return cleaned
    except Exception as exc:
        logger.warning(
            "today_tasks_llm_failed | day=%s | error=%s",
            day_number,
            str(exc),
        )
        return None


def _today_tasks_payload(
    *,
    sprint: Sprint | None,
    day_number: int | None = None,
    day_title: str | None = None,
    overview: str | None = None,
    time_estimate: str | None = None,
    source: str | None = None,
    tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "has_sprint": sprint is not None,
        "sprint_id": sprint.id if sprint else None,
        "day_number": day_number,
        "day_title": day_title,
        "overview": overview,
        "time_estimate": time_estimate,
        "source": source,
        "can_execute": sprint is not None and day_number is not None,
        "tasks": tasks or [],
    }


def _seed_ad_factory_videos_after_day_3(db: Session, sprint: Sprint) -> None:
    """Seed starter videos for Ad Factory once Day 3 is completed."""
    from app.modules.creative.services import list_assets_for_pack
    from app.modules.creative.tools import render_video

    assets = list_assets_for_pack(db, sprint.pack_id)
    has_video_assets = any(getattr(asset, "type", None) == "video" for asset in assets)
    if has_video_assets:
        return
    render_video(db=db, pack_id=sprint.pack_id, count=4, sprint_day=4)


def _effective_current_day(sprint: Sprint, pack: Pack | None) -> int:
    """Clamp Step 3 until Step 2 onboarding finalization has succeeded."""
    current_day = sprint.current_day
    if pack and current_day >= 3 and pack.onboarding_completed_at is None:
        return 2
    return current_day


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
def create_sprint_for_pack(
    db: Session,
    pack_id: UUID,
    started_at: datetime | None = None,
    *,
    commit: bool = True,
) -> Sprint:
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
    if commit:
        db.commit()
    if commit and sprint.current_day == 3:
        try:
            _seed_ad_factory_videos_after_day_3(db, sprint)
        except Exception as exc:
            # Day completion should succeed even if starter video seeding fails.
            logger.warning(
                "day3_video_seed_failed | sprint_id=%s | pack_id=%s | error=%s",
                sprint.id,
                sprint.pack_id,
                str(exc),
            )
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

    if day_number == 2 and pack.onboarding_completed_at is None:
        raise ValueError(
            "Generate your Brand OS to complete Step 2 before moving to Step 3."
        )
    
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
    
    # Sync Pack fields for Day 1-3
    if user_selections and day_number in (1, 2, 3):
        if day_number == 1:
            # Day 1: Offer
            if "offer_one_liner" in user_selections:
                pack.offer_one_liner = (user_selections["offer_one_liner"] or "").strip() or None
        elif day_number == 2:
            # Day 2: USP + Audience - set pain, outcome, target_audience
            if "primary_pain" in user_selections:
                pack.primary_pain = (user_selections["primary_pain"] or "").strip() or None
            if "primary_outcome" in user_selections:
                pack.primary_outcome = (user_selections["primary_outcome"] or "").strip() or None
            if "target_audience" in user_selections:
                pack.target_audience = (user_selections["target_audience"] or "").strip() or None
        elif day_number == 3:
            answers = dict(pack.onboarding_answers or {})
            if "pitch_script" in user_selections:
                answers["pitch_script"] = (user_selections["pitch_script"] or "").strip()
            if "voice_notes_sent" in user_selections:
                answers["voice_notes_sent"] = str(user_selections["voice_notes_sent"]).strip()
            pack.onboarding_answers = answers

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
    Days beyond current_day are locked. Some days also have completion gates.
    """
    if day_number < 0 or day_number > 14:
        return None
    sprint = get_active_sprint_for_pack(db, pack_id)
    if not sprint:
        return None
    card = get_day_card(db, sprint.id, day_number)
    if not card:
        return None

    pack = db.query(Pack).filter(Pack.id == sprint.pack_id).first()
    effective_current_day = _effective_current_day(sprint, pack)
    unlocked = day_number <= effective_current_day
    blocker_message: str | None = None
    completion_blocked_message: str | None = None

    if day_number == 3 and pack and pack.onboarding_completed_at is None:
        unlocked = False
        blocker_message = "Complete Step 2 and generate your Brand OS first."

    if unlocked and pack:
        from app.core.gates import (
            can_complete_day,
            can_pass_day7_gate,
            can_pass_day8_gate,
        )
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

        if unlocked and card.completed_at is None:
            can_complete, msg = can_complete_day(db, card, day_number, pack)
            if not can_complete:
                completion_blocked_message = msg

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
        "completion_blocked_message": completion_blocked_message,
    }


@log_service_action()
def get_or_generate_today_tasks(db: Session, pack_id: UUID) -> dict[str, Any]:
    """Get cached current-day checklist tasks for overview, generating if needed."""
    sprint = get_active_sprint_for_pack(db, pack_id)
    if not sprint:
        return _today_tasks_payload(
            sprint=None,
            overview="Start your 14-day sprint to unlock today's task checklist.",
            time_estimate="10 mins",
        )

    pack = db.query(Pack).filter(Pack.id == sprint.pack_id).first()
    day_number = _effective_current_day(sprint, pack)
    day_def = get_day_definition(day_number)
    fallback_labels, overview = _fallback_task_labels(day_number, sprint.mode)
    day_title = str(day_def.get("title") or f"Day {day_number}")
    card = get_day_card(db, sprint.id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")

    cache = _get_cached_today_tasks(card, day_number)
    if not cache:
        context = _pack_context_for_today_tasks(pack) if pack else "No pack context available yet."
        llm_labels = _generate_today_task_labels_with_llm(
            day_number=day_number,
            day_title=day_title,
            mode=sprint.mode,
            overview=overview,
            fallback_labels=fallback_labels,
            pack_context=context,
        )
        source = "llm" if llm_labels else "fallback"
        labels = llm_labels or fallback_labels
        tasks = _build_task_items(labels)
        cache = {
            "day_number": day_number,
            "source": source,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": tasks,
        }
        ai_output = card.ai_output if isinstance(card.ai_output, dict) else {}
        ai_output = dict(ai_output)
        ai_output[TODAY_TASKS_CACHE_KEY] = cache
        card.ai_output = ai_output
        db.commit()
        db.refresh(card)
        logger.info(
            "today_tasks_generated | pack_id=%s | sprint_id=%s | day=%s | source=%s | task_count=%s",
            pack_id,
            sprint.id,
            day_number,
            source,
            len(tasks),
        )

    return _today_tasks_payload(
        sprint=sprint,
        day_number=day_number,
        day_title=day_title,
        overview=overview,
        time_estimate="15-30 mins",
        source=str(cache.get("source") or "fallback"),
        tasks=_normalise_cached_tasks(cache.get("tasks")),
    )


@log_service_action()
def toggle_today_task_check(
    db: Session,
    pack_id: UUID,
    day_number: int,
    task_id: str,
    checked: bool,
) -> dict[str, Any]:
    """Toggle persisted checklist item for current sprint day."""
    sprint = get_active_sprint_for_pack(db, pack_id)
    if not sprint:
        raise ValueError("No active sprint")
    pack = db.query(Pack).filter(Pack.id == sprint.pack_id).first()
    effective_current_day = _effective_current_day(sprint, pack)
    if day_number != effective_current_day:
        raise StaleDayError(
            f"Checklist moved to Day {effective_current_day}. Refresh and try again."
        )

    card = get_day_card(db, sprint.id, day_number)
    if not card:
        raise ValueError(f"No day card for day {day_number}")

    cache = _get_cached_today_tasks(card, day_number)
    if not cache:
        get_or_generate_today_tasks(db, pack_id)
        card = get_day_card(db, sprint.id, day_number)
        if not card:
            raise ValueError(f"No day card for day {day_number}")
        cache = _get_cached_today_tasks(card, day_number)
    if not cache:
        raise ValueError("Checklist unavailable")

    task_found = False
    for task in cache["tasks"]:
        if task["id"] == task_id:
            task["checked"] = bool(checked)
            task_found = True
            break
    if not task_found:
        raise ValueError("Task not found")

    ai_output = card.ai_output if isinstance(card.ai_output, dict) else {}
    ai_output = dict(ai_output)
    ai_output[TODAY_TASKS_CACHE_KEY] = cache
    card.ai_output = ai_output
    db.commit()

    logger.info(
        "today_task_toggled | pack_id=%s | sprint_id=%s | day=%s | task_id=%s | checked=%s",
        pack_id,
        sprint.id,
        day_number,
        task_id,
        checked,
    )

    return get_or_generate_today_tasks(db, pack_id)
