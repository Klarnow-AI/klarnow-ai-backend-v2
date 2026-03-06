"""Sprint and DayCard Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DayCardRead(BaseModel):
    id: UUID
    sprint_id: UUID
    day_number: int
    ai_output: dict | None
    user_action: str | None
    definition_of_done: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DayCardUpdate(BaseModel):
    ai_output: dict | None = None
    user_action: str | None = None
    definition_of_done: str | None = None
    completed_at: datetime | None = None

    model_config = {"extra": "forbid"}


class SprintRead(BaseModel):
    id: UUID
    pack_id: UUID
    status: str
    mode: str
    current_day: int
    success_metrics: dict | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    day_cards: list[DayCardRead] = []

    model_config = {"from_attributes": True}


class SprintCreate(BaseModel):
    """Create a new sprint for a pack. Only one active sprint per pack."""

    model_config = {"extra": "forbid"}


class SprintUpdate(BaseModel):
    status: str | None = None
    current_day: int | None = None
    completed_at: datetime | None = None

    model_config = {"extra": "forbid"}


class SprintDayDetail(BaseModel):
    """Detail for one day in a 14-day sprint (MVP)."""

    day_number: int
    title: str
    ai_output: dict | None
    user_action: str | None
    definition_of_done: str | None
    completed_at: datetime | None
    unlocked: bool
    blocker_message: str | None = None
    completion_blocked_message: str | None = None


class TodayTaskItem(BaseModel):
    id: str
    label: str
    checked: bool = False

    model_config = {"extra": "forbid"}


class SprintTodayTasksRead(BaseModel):
    has_sprint: bool
    sprint_id: UUID | None = None
    day_number: int | None = None
    day_title: str | None = None
    overview: str | None = None
    time_estimate: str | None = None
    source: str | None = None
    can_execute: bool = False
    tasks: list[TodayTaskItem] = Field(default_factory=list)


class TodayTaskToggleBody(BaseModel):
    day_number: int = Field(..., ge=0, le=14)
    task_id: str = Field(..., min_length=1)
    checked: bool

    model_config = {"extra": "forbid"}


class DayCompleteRequest(BaseModel):
    """
    Request body for completing a day.
    Day 1 & 2: user_selections synced to Pack. Day 3: optional pitch_script, voice_notes_sent.
    """
    user_selections: dict | None = Field(
        None,
        description="Day 1: offer_one_liner. Day 2: primary_pain, primary_outcome. Day 3: pitch_script, voice_notes_sent (optional)."
    )

    model_config = {"extra": "forbid"}


class SuggestDayResponse(BaseModel):
    """Suggested values for a sprint day's fields (Day 1, 2, or 3)."""
    offer_one_liner: str | None = None
    primary_pain: str | None = None
    primary_outcome: str | None = None
    pitch_script: str | None = None

    model_config = {"extra": "forbid"}


class SuggestFieldRequest(BaseModel):
    """Request body for POST suggest-field: day, field, optional current value."""
    day: int = Field(..., ge=1, le=3, description="Sprint day 1, 2, or 3")
    field: str = Field(..., description="offer_one_liner | primary_pain | primary_outcome | pitch_script")
    current_value: str | None = Field(None, description="Current value to refine")

    model_config = {"extra": "forbid"}


class SuggestFieldResponse(BaseModel):
    suggestion: str
