"""Landing context API: state for landing page UI."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.landing.next_action import get_next_action
from app.modules.landing.schemas import (
    LandingContext,
    NextAction,
    LandingCompleteBody,
    LandingCompleteResponse,
    ProfileResponse,
)
from app.modules.landing.services import get_landing_context, landing_complete
from app.modules.packs.models import User

router = APIRouter()


@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Return current user profile (email, created_at, last_activity_at)."""
    return ProfileResponse(
        email=current_user.email,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        last_activity_at=(
            current_user.last_activity_at.isoformat()
            if current_user.last_activity_at
            else None
        ),
    )


@router.get("/landing-context", response_model=LandingContext)
def landing_context(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return pack, stage, sprintDay, leadCount for the landing state-machine UI."""
    return get_landing_context(db, current_user.id)


@router.get("/next-action", response_model=NextAction)
def next_action(
    pack_id: UUID | None = Query(None, description="Pack id; if omitted, first pack is used"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return next action and up to 3 suggestion chips for Command Centre / landing."""
    data = get_next_action(db, current_user.id, pack_id)
    return NextAction(
        action_text=data["action_text"],
        action_chips=data["action_chips"],
        stage=data["stage"],
        can_proceed=data["can_proceed"],
        blocker_message=data.get("blocker_message"),
        why_it_matters=data.get("why_it_matters"),
        time_estimate=data.get("time_estimate"),
        progress_counters=data.get("progress_counters"),
    )


@router.post("/landing-complete", response_model=LandingCompleteResponse)
def landing_complete_route(
    body: LandingCompleteBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete landing onboarding: 3 questions + Pack name. Creates Pack + Sprint (Day 0-14). Redirect to /packs/{id}."""
    pack_id, redirect = landing_complete(
        db,
        current_user.id,
        pack_name=body.pack_name,
        what_do_you_sell=body.what_do_you_sell,
        who_is_it_for=body.who_is_it_for,
        where_are_you_based=body.where_are_you_based,
    )
    return LandingCompleteResponse(pack_id=str(pack_id), redirect=redirect)
