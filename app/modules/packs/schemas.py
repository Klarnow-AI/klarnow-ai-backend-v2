"""Pydantic schemas for packs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    primary_pain: str | None = None
    primary_outcome: str | None = None
    hero_angle: str | None = None

    model_config = {"from_attributes": True}


class PackPatch(BaseModel):
    """Partial update: name, client_id, pack_type, core_concept; Day 0: brand_name, primary_cta, USP, proof; optional onboarding_answers merge (e.g. has_existing_brand)."""

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
    onboarding_answers: dict | None = None

    model_config = {"extra": "forbid"}


class PackList(BaseModel):
    items: list[PackRead]
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


class GenerateLogoBody(BaseModel):
    """Body for generate-logo (Gemini image generation). Prompt template: Create a [image type] for [brand]. The design should be [style], with a [color scheme]."""

    brand_name: str
    prompt: str | None = None  # style description
    color_scheme: str | None = None  # e.g. "blue and white", "neutral and versatile"
    color_palette: dict | None = None  # brand colors e.g. {"primary": "#hex", "secondary": "#hex", "accent": "#hex"}
    brand_os_summary: str | None = None  # Brand OS context (mission, positioning, etc.)


class GenerateLogoResponse(BaseModel):
    """Response from generate-logo."""

    logo_url: str
    wordmark_svg_or_url: str | None = None


class UploadLogoResponse(BaseModel):
    """Response from upload-logo."""

    logo_url: str


class MockupItemResponse(BaseModel):
    """Single mockup image in generate-mockups response."""

    id: str
    url: str
    width: int | None = None
    height: int | None = None
    size: str | None = None


class GenerateMockupsResponse(BaseModel):
    """Response from brand-showcase generate-mockups."""

    items: list[MockupItemResponse]


class SuggestTypographyBody(BaseModel):
    """Optional current values for refine."""

    current_headline: str | None = None
    current_body: str | None = None


class SuggestTypographyResponse(BaseModel):
    headline_font: str
    body_font: str


class SuggestPaletteBody(BaseModel):
    """Optional current palette for refine (e.g. primary, secondary, accent hex)."""

    current_palette: dict | None = None


class SuggestPaletteResponse(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str | None = None
    surface: str | None = None


class OnboardingComplete(BaseModel):
    """Body for completing onboarding (optional; just POST to complete)."""

    pass


class OnboardingCompleteResponse(BaseModel):
    """Response from onboarding/complete: pack plus whether the brand is existing."""

    pack: PackRead
    is_existing_brand: bool


class OnboardingCompleteAccepted(BaseModel):
    """202 response when onboarding completion is running in the background. Poll GET pack until onboarding_background_completed_at is set."""

    status: str = "processing"
    pack_id: str


# --- Pack summary (overview from Brand OS → Proof Vault) ---


class BrandOSSummary(BaseModel):
    mission: str | None = None
    vision: str | None = None
    has_positioning: bool = False


class CampaignSummary(BaseModel):
    primary_cta: str | None = None
    goal_summary: str | None = None


class ConversionPageSummary(BaseModel):
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
    conversion_page: ConversionPageSummary | None = None
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
