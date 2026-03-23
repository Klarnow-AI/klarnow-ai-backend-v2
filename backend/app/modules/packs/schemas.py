"""Pydantic schemas for packs."""

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.storage import resolve_asset_reference
from app.modules.brand_os.schemas import BrandOSRead


PACK_TYPES = ("enquiries", "quotes", "sales")


class PackBase(BaseModel):
    name: str


class PackCreate(PackBase):
    pack_type: str = "enquiries"


class PackRead(PackBase):
    id: UUID
    status: str
    pack_type: str = "enquiries"
    onboarding_answers: dict | None = None
    onboarding_completed_at: datetime | None = None
    onboarding_background_completed_at: datetime | None = None
    core_concept: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID
    client_id: UUID | None = None
    brand_name: str | None = None
    primary_cta: str | None = None
    usp_category: str | None = None
    usp_statement: str | None = None
    usp_proof: str | None = None
    usp_locked_line: str | None = None
    proof_types: list[str] | None = None
    proof_text: str | None = None
    day_0_completed_at: datetime | None = None
    offer_one_liner: str | None = None
    target_audience: str | None = None
    primary_pain: str | None = None
    primary_outcome: str | None = None
    hero_angle: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def normalize_onboarding_asset_urls(self):
        answers = self.onboarding_answers
        if not isinstance(answers, dict):
            return self

        normalized = dict(answers)
        for key in (
            "wordmark_svg_or_url",
            "wordmark_result",
            "generated_logo_url",
            "transparent_logo_url",
        ):
            value = normalized.get(key)
            if isinstance(value, str):
                normalized_value = resolve_asset_reference(value, expires_in=86400 * 7)
                if normalized_value:
                    normalized[key] = normalized_value

        raw_suggested = normalized.get("suggested_logos")
        if isinstance(raw_suggested, str):
            try:
                suggested = json.loads(raw_suggested)
            except (json.JSONDecodeError, TypeError):
                suggested = None
            if isinstance(suggested, list):
                normalized["suggested_logos"] = json.dumps(
                    [
                        resolve_asset_reference(item, expires_in=86400 * 7) or item
                        if isinstance(item, str)
                        else item
                        for item in suggested
                    ]
                )

        self.onboarding_answers = normalized
        return self


class PackPatch(BaseModel):
    """Partial update: name, client_id, pack_type, core_concept; Day 0: brand_name, primary_cta, USP, proof; Day 1-3: offer_one_liner, target_audience, primary_pain, primary_outcome, hero_angle."""

    name: str | None = None
    client_id: UUID | None = None
    pack_type: str | None = None
    core_concept: str | None = None
    brand_name: str | None = None
    primary_cta: str | None = None
    usp_category: str | None = None
    usp_statement: str | None = None
    usp_proof: str | None = None
    usp_locked_line: str | None = None
    proof_types: list[str] | None = None
    proof_text: str | None = None
    offer_one_liner: str | None = None
    target_audience: str | None = None
    primary_pain: str | None = None
    primary_outcome: str | None = None
    hero_angle: str | None = None
    onboarding_answers: dict | None = None

    model_config = {"extra": "forbid"}


class DayReadinessResponse(BaseModel):
    """Day 0-3 readiness: whether all required questions have been answered."""

    ready: bool


class PackListItem(PackRead):
    """Pack with campaign status for list views."""

    campaign_is_active: bool | None = None


class PackList(BaseModel):
    items: list[PackListItem]
    total: int


# Onboarding answer keys: has_existing_brand, brand_input_type, brand_url, pasted_copy,
# logo_file_key, extracted_brand, brand_name, vibe_chips, wordmark_result, palette, q1..qN (blockers).
ONBOARDING_MAX_QUESTIONS = 20


class OnboardingSubmit(BaseModel):
    """Submit onboarding answers (up to ONBOARDING_MAX_QUESTIONS keys)."""

    answers: dict = Field(..., description="Onboarding keys: branch, path-specific data, blocker q1..qN")

    @model_validator(mode="after")
    def check_max_questions(self):
        if len(self.answers) > ONBOARDING_MAX_QUESTIONS:
            raise ValueError(f"At most {ONBOARDING_MAX_QUESTIONS} onboarding answers allowed")
        return self


class ExtractBrandBody(BaseModel):
    """Body for extract-brand: one of url, pasted_text, or logo_file_key."""

    input_type: str  # "url" | "paste" | "logo"
    url: str | None = None
    pasted_text: str | None = None
    logo_file_key: str | None = None


class ExtractBrandResponse(BaseModel):
    """Response from extract-brand with rich brand profile data."""

    brand_name: str
    offer_cues: list[str]
    tagline: str | None = None
    description: str | None = None
    industry: str | None = None
    contact_info: dict = Field(default_factory=dict)
    social_links: list[str] = Field(default_factory=list)
    logo_url: str | None = None
    color_candidates: list[str] = Field(default_factory=list)
    raw_extract: dict | None = None


class GenerateStarterBrandBody(BaseModel):
    """Body for generate-starter-brand."""

    brand_name: str
    vibe_chips: list[str]


class GenerateStarterBrandResponse(BaseModel):
    """Response from generate-starter-brand."""

    wordmark_svg_or_url: str
    palette: dict  # e.g. primary, secondary, accent
    logo_url: str | None = None
    transparent_logo_url: str | None = None


class GenerateLogoBody(BaseModel):
    """Body for generate-logo using the configured logo image provider."""

    brand_name: str
    prompt: str | None = None  # style description
    color_scheme: str | None = None  # e.g. "blue and white", "neutral and versatile"
    color_palette: dict | None = None  # brand colors e.g. {"primary": "#hex", "secondary": "#hex", "accent": "#hex"}
    brand_os_summary: str | None = None  # Brand OS context (mission, positioning, etc.)


class GenerateLogoResponse(BaseModel):
    """Response from generate-logo."""

    logo_url: str
    wordmark_svg_or_url: str | None = None
    transparent_logo_url: str | None = None


class UploadLogoResponse(BaseModel):
    """Response from upload-logo."""

    logo_url: str


class SuggestTypographyBody(BaseModel):
    """Optional current values for refine."""

    current_headline: str | None = None
    current_body: str | None = None


class SuggestTypographyResponse(BaseModel):
    headline_font: str
    body_font: str
    source: Literal["ai", "fallback"] = "ai"
    reason: str | None = None


class SuggestPaletteBody(BaseModel):
    """Optional current palette for refine (e.g. primary, secondary, accent hex)."""

    current_palette: dict | None = None


class SuggestPaletteResponse(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str | None = None
    surface: str | None = None
    source: Literal["ai", "fallback"] = "ai"
    reason: str | None = None


class OnboardingComplete(BaseModel):
    """Body for completing onboarding (optional; just POST to complete)."""

    pass


class OnboardingCompleteResponse(BaseModel):
    """Response from onboarding/complete finalization."""

    pack: PackRead
    is_existing_brand: bool
    brand_os: BrandOSRead | None = None
    starter_brand: GenerateStarterBrandResponse | None = None
    logo: GenerateLogoResponse | None = None


class OnboardingCompleteAccepted(BaseModel):
    """202 response when onboarding completion is running in the background. Poll GET pack until onboarding_background_completed_at is set."""

    status: str = "processing"
    pack_id: str
    job_id: str | None = None


class OnboardingStageStatus(BaseModel):
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    last_error: str | None = None


class OnboardingJobStatusResponse(BaseModel):
    """Current state of the durable onboarding background job."""

    status: str
    job_id: str | None = None
    attempt: int = 0
    max_attempts: int = 3
    queued_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    last_error: str | None = None
    current_stage: str | None = None
    stages: dict[str, OnboardingStageStatus] | None = None


# --- Pack summary (overview from Brand OS → Proof Vault) ---


class BrandOSSummary(BaseModel):
    mission: str | None = None
    vision: str | None = None
    has_positioning: bool = False


class CampaignSummary(BaseModel):
    primary_cta: str | None = None
    goal_summary: str | None = None


class WebsiteSummary(BaseModel):
    live_url: str | None = None
    published_at: str | None = None  # ISO datetime or None if draft only


class PlanTrackerSummary(BaseModel):
    horizon: str | None = None
    sprint_day: int | None = None  # 1-7 for 7-day sprint
    has_sprint: bool = False


class LeadsSummary(BaseModel):
    total: int = 0
    qualified: int = 0


class ProposalsSummary(BaseModel):
    total: int = 0
    sent: int = 0
    accepted: int = 0
    declined: int = 0


class InvoicesSummary(BaseModel):
    total: int = 0
    sent: int = 0
    paid: int = 0
    overdue: int = 0


class PackSummaryResponse(BaseModel):
    pack: PackRead
    brand_os: BrandOSSummary | None = None
    campaign: CampaignSummary | None = None
    website: WebsiteSummary | None = None
    plan_tracker: PlanTrackerSummary | None = None
    leads: LeadsSummary = Field(default_factory=LeadsSummary)
    proposals: ProposalsSummary = Field(default_factory=ProposalsSummary)
    invoices: InvoicesSummary = Field(default_factory=InvoicesSummary)
    proofs_count: int = 0
    assets_count: int = 0


# --- Pack gates (section unlock status) ---


class GateStatus(BaseModel):
    passed: bool
    message: str | None = None


class SectionUnlock(BaseModel):
    unlocked: bool
    reason: str | None = None


class PackGatesResponse(BaseModel):
    pack_gate: GateStatus
    paywall_gate: GateStatus
    day7_gate: GateStatus
    day8_gate: GateStatus
    current_day: int | None = None
    has_sprint: bool = False
    sections: dict[str, SectionUnlock]
