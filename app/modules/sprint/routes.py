"""Sprint API: get/create sprint, day cards, complete day, Day 14 reload."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError, map_value_error_to_app_error
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.sprint.schemas import (
    SprintRead,
    SprintCreate,
    DayCardRead,
    DayCardUpdate,
    SprintDayDetail,
    SprintTodayTasksRead,
    TodayTaskToggleBody,
    DayCompleteRequest,
    SuggestDayResponse,
    SuggestFieldRequest,
    SuggestFieldResponse,
)
from app.modules.sprint.services import (
    get_sprint_for_pack,
    get_sprint_by_id,
    create_sprint_for_pack,
    get_day_card,
    update_day_card,
    complete_day,
    complete_sprint_and_reload,
    get_sprint_day_detail,
    get_or_generate_today_tasks,
    toggle_today_task_check,
    StaleDayError,
)
from app.modules.sprint.suggestions import suggest_day_fields, suggest_sprint_field

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


@router.get("/packs/{pack_id}/sprint", response_model=SprintRead | None)
def get_sprint(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active sprint for pack, or most recent if none active."""
    _ensure_pack_access(db, pack_id, current_user.id)
    sprint = get_sprint_for_pack(db, pack_id)
    if not sprint:
        return None
    return SprintRead.model_validate(sprint)


@router.post(
    "/packs/{pack_id}/sprint",
    response_model=SprintRead,
    status_code=status.HTTP_201_CREATED,
)
def create_sprint(
    pack_id: UUID,
    body: SprintCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new 14-day sprint for the pack (with DayCards 0-14). Fails if one is already active."""
    _ensure_pack_access(db, pack_id, current_user.id)
    try:
        sprint = create_sprint_for_pack(db, pack_id)
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e
    return SprintRead.model_validate(sprint)


@router.get(
    "/packs/{pack_id}/sprint/day/{day_number}",
    response_model=SprintDayDetail | None,
)
def get_sprint_day(
    pack_id: UUID,
    day_number: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detail for one day (0-14) of the pack's active sprint."""
    _ensure_pack_access(db, pack_id, current_user.id)
    detail = get_sprint_day_detail(db, pack_id, day_number)
    return SprintDayDetail.model_validate(detail) if detail else None


@router.get(
    "/packs/{pack_id}/sprint/today-tasks",
    response_model=SprintTodayTasksRead,
)
def get_today_tasks(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current sprint-day checklist for the pack overview page."""
    _ensure_pack_access(db, pack_id, current_user.id)
    data = get_or_generate_today_tasks(db, pack_id)
    return SprintTodayTasksRead.model_validate(data)


@router.patch(
    "/packs/{pack_id}/sprint/today-tasks",
    response_model=SprintTodayTasksRead,
)
def patch_today_task(
    pack_id: UUID,
    body: TodayTaskToggleBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle one checklist item for the current sprint day."""
    _ensure_pack_access(db, pack_id, current_user.id)
    try:
        data = toggle_today_task_check(
            db=db,
            pack_id=pack_id,
            day_number=body.day_number,
            task_id=body.task_id,
            checked=body.checked,
        )
    except StaleDayError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e
    return SprintTodayTasksRead.model_validate(data)


@router.post(
    "/packs/{pack_id}/sprint/suggest-day/{day_number}",
    response_model=SuggestDayResponse,
)
def suggest_day(
    pack_id: UUID,
    day_number: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return suggested values for a sprint day's fields (Day 1, 2, or 3). Used to pre-fill modals."""
    _ensure_pack_access(db, pack_id, current_user.id)
    if day_number not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="day_number must be 1, 2, or 3")
    data = suggest_day_fields(db, pack_id, day_number)
    return SuggestDayResponse(**data)


@router.post(
    "/packs/{pack_id}/sprint/suggest-field",
    response_model=SuggestFieldResponse,
)
def suggest_field(
    pack_id: UUID,
    body: SuggestFieldRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest or refine a single sprint day field (Refine with AI)."""
    _ensure_pack_access(db, pack_id, current_user.id)
    suggestion_data = suggest_sprint_field(
        db, pack_id, body.day, body.field, body.current_value
    )
    return SuggestFieldResponse(**suggestion_data)


@router.patch("/packs/{pack_id}/sprint/{sprint_id}/day/{day_number}", response_model=DayCardRead)
def patch_day_card(
    pack_id: UUID,
    sprint_id: UUID,
    day_number: int,
    body: DayCardUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a day card's ai_output, user_action, definition_of_done, or completed_at."""
    _ensure_pack_access(db, pack_id, current_user.id)
    sprint = get_sprint_by_id(db, sprint_id, pack_id=pack_id)
    if not sprint:
        raise NotFoundError("Sprint not found")
    card = get_day_card(db, sprint_id, day_number)
    if not card:
        raise NotFoundError("Day card not found")
    data = body.model_dump(exclude_unset=True)
    card = update_day_card(db, card, **data)
    return DayCardRead.model_validate(card)


@router.post("/packs/{pack_id}/sprint/{sprint_id}/day/{day_number}/complete", response_model=SprintRead)
def complete_sprint_day(
    pack_id: UUID,
    sprint_id: UUID,
    day_number: int,
    body: DayCompleteRequest | None = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a day as complete and advance current_day. If day 14, marks sprint completed.
    For Day 1 & 2, accepts user_selections to sync Pack fields.
    """
    _ensure_pack_access(db, pack_id, current_user.id)
    sprint = get_sprint_by_id(db, sprint_id, pack_id=pack_id)
    if not sprint:
        raise NotFoundError("Sprint not found")
    
    user_selections = body.user_selections if body else None
    
    try:
        sprint = complete_day(db, sprint, day_number, user_selections)
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e
    
    return SprintRead.model_validate(sprint)


@router.post(
    "/packs/{pack_id}/sprint/{sprint_id}/check-in",
    response_model=SprintRead,
    status_code=status.HTTP_201_CREATED,
)
def day_14_checkin(
    pack_id: UUID,
    sprint_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Day 14 check-in: complete current sprint and create Sprint 2. Returns the new sprint."""
    _ensure_pack_access(db, pack_id, current_user.id)
    try:
        new_sprint = complete_sprint_and_reload(db, pack_id, sprint_id)
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e
    return SprintRead.model_validate(new_sprint)
