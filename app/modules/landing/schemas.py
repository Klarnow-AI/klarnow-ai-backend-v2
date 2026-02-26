"""Landing context schema for state-machine UI."""

from pydantic import BaseModel, Field


class LandingPack(BaseModel):
    id: str
    name: str


class LandingContext(BaseModel):
    pack: LandingPack | None = None
    stage: str  # no_pack | brand_os_done | page_live | sprint | leads
    sprint_day: int | None = Field(None, alias="sprintDay")
    lead_count: int | None = Field(None, alias="leadCount")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class NextActionChip(BaseModel):
    label: str
    href: str | None = None


class NextAction(BaseModel):
    action_text: str = Field(..., alias="actionText")
    action_chips: list[NextActionChip] = Field(..., alias="actionChips")
    stage: str = Field(...)
    can_proceed: bool = Field(..., alias="canProceed")
    blocker_message: str | None = Field(None, alias="blockerMessage")
    why_it_matters: str | None = Field(None, alias="whyItMatters")
    time_estimate: str | None = Field(None, alias="timeEstimate")
    progress_counters: dict[str, str] | None = Field(None, alias="progressCounters")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class LandingCompleteBody(BaseModel):
    """Landing onboarding: 3 core questions + Pack name. Creates Pack + Sprint."""

    pack_name: str
    what_do_you_sell: str
    who_is_it_for: str
    where_are_you_based: str

    model_config = {"extra": "forbid"}


class LandingCompleteResponse(BaseModel):
    pack_id: str
    redirect: str


class ProfileResponse(BaseModel):
    email: str
    created_at: str  # ISO datetime
    last_activity_at: str | None  # ISO datetime or None
