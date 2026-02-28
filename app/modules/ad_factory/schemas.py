"""Ad Factory V2 Pydantic schemas. Structured JSON only—no free-form text."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProofAsset(BaseModel):
    asset_type: Literal[
        "testimonial",
        "case_study",
        "numbers",
        "screenshots",
        "before_after",
        "ugc",
        "press",
        "certification",
    ]
    label: str = Field(..., min_length=1, max_length=140)
    uri: str | None = Field(None, max_length=2048)
    notes: str | None = Field(None, max_length=400)


class CTADestination(BaseModel):
    destination_type: Literal[
        "cal_link",
        "landing_page",
        "dm",
        "whatsapp",
        "phone",
        "checkout",
    ]
    value: str = Field(..., min_length=3, max_length=2048)


class BrandBrief(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=120)
    offer: str = Field(..., min_length=2, max_length=240)
    audience: str = Field(..., min_length=2, max_length=180)
    location: str = Field(..., min_length=2, max_length=120)
    primary_outcome: str = Field(..., min_length=2, max_length=180)
    proof_assets: list[ProofAsset] = Field(default_factory=list)
    tone: Literal["direct", "calm", "bold", "friendly", "luxury", "playful"]
    face_on_camera: bool
    price_position: Literal["budget", "mid", "premium"]
    cta_action: Literal["book", "call", "dm", "visit", "buy", "whatsapp", "apply"]
    cta_destination: CTADestination
    usp: str | None = Field(None, max_length=240)
    core_concept: str | None = Field(None, max_length=120)


class PackSnapshot(BaseModel):
    pack_id: str = Field(..., min_length=3, max_length=64)
    pack_name: str = Field(..., min_length=2, max_length=120)
    sprint_id: str = Field(..., min_length=3, max_length=64)
    day: int = Field(..., ge=1, le=14)
    stage: Literal["clarity", "setup", "publish", "traffic", "follow_up", "close"]
    traffic_source: str = Field(default="unknown", max_length=32)


class Engine0PackContextOutput(BaseModel):
    objective_type: Literal["lead_gen", "booking", "purchase"]
    funnel_stage: Literal["cold", "warm", "hot", "retargeting"]
    awareness_level: Literal["unaware", "problem_aware", "solution_aware", "offer_aware"]
    traffic_source: str = "unknown"


class ProofStrategyOutput(BaseModel):
    strategy_id: str
    fallback_used: bool


class MessagingConstraints(BaseModel):
    no_assumptions: bool = True
    no_freeform: bool = True
    disallowed_claims: list[str] = Field(default_factory=list)


class Engine1ContextBuilderOutput(BaseModel):
    summary: str = Field(..., max_length=280)
    pains: list[str] = Field(..., min_length=3, max_length=3)
    outcomes: list[str] = Field(..., min_length=3, max_length=3)
    differentiators: list[str] = Field(..., min_length=3, max_length=3)
    proof_strategy: ProofStrategyOutput
    messaging_constraints: MessagingConstraints


class VariantPlan(BaseModel):
    slot: Literal["A", "B", "C"]
    intent: Literal["emotion_led", "logic_led", "offer_led"]
    path: Literal[
        "pain_escape",
        "status_upgrade",
        "convenience",
        "trust_safety",
        "transformation",
    ]
    treatment: Literal[
        "talking_head_authority",
        "cinematic_process",
        "ugc_customer_story",
        "offer_smash",
    ]
    hook_type: Literal[
        "question",
        "bold_claim",
        "relatable_moment",
        "before_after_tease",
        "contrarian_truth",
        "stop_doing_this",
    ]


class Engine2VariationControllerOutput(BaseModel):
    variant_plans: list[VariantPlan] = Field(..., min_length=3, max_length=3)


class PatternSelection(BaseModel):
    slot: Literal["A", "B", "C"]
    pattern_id: str
    hook_id: str
    proof_strategy_id: str
    cta_id: str
    line_template_ids: dict[str, list[str]]


class Engine3PatternAssemblerOutput(BaseModel):
    selections: list[PatternSelection] = Field(..., min_length=3, max_length=3)


class ScriptBeat(BaseModel):
    beat_name: Literal["hook", "problem", "mechanism", "proof", "offer", "cta"]
    text: str = Field(..., max_length=320)


class Script(BaseModel):
    beats: list[ScriptBeat] = Field(..., min_length=6, max_length=6)
    timing_rules_satisfied: bool


class CTAResolved(BaseModel):
    cta_action: str
    destination_type: str
    destination_value: str
    mid_line: str
    end_line: str


class VariantScripts(BaseModel):
    slot: Literal["A", "B", "C"]
    core_concept: str = Field(..., max_length=60)
    hook_line: str = Field(..., max_length=60)
    script_15s: Script
    script_30s: Script
    cta: CTAResolved


class Engine4ScriptConverterOutput(BaseModel):
    scripts: list[VariantScripts] = Field(..., min_length=3, max_length=3)


class Shot(BaseModel):
    index: int = Field(..., ge=1, le=8)
    shot_type: Literal[
        "pattern_interrupt",
        "establishing",
        "mechanism_1",
        "mechanism_2",
        "proof_overlay",
        "human_moment",
        "result_reveal",
        "cta_frame",
    ]
    description: str = Field(..., max_length=200)
    on_screen_text: str = Field(..., min_length=1, max_length=60)
    nanobanana_prompt: str = Field(..., min_length=10, max_length=800)
    caption_overlay: dict = Field(default_factory=lambda: {"enabled": True})


class VariantShotPlan(BaseModel):
    slot: Literal["A", "B", "C"]
    shots: list[Shot] = Field(..., min_length=8, max_length=8)
    pacing: dict


class Engine5VisualDirectorOutput(BaseModel):
    shot_plans: list[VariantShotPlan] = Field(..., min_length=3, max_length=3)


class KlingPrompt(BaseModel):
    prompt: str = Field(..., min_length=20, max_length=4000)
    duration_seconds: Literal[15, 30]


class VariantKlingPrompts(BaseModel):
    slot: Literal["A", "B", "C"]
    kling_15s: KlingPrompt
    kling_30s: KlingPrompt
    render_requirements: dict


class Engine6KlingAssemblerOutput(BaseModel):
    kling_prompts: list[VariantKlingPrompts] = Field(..., min_length=3, max_length=3)


class Variant(BaseModel):
    slot: Literal["A", "B", "C"]
    intent: Literal["emotion_led", "logic_led", "offer_led"]
    path: str
    treatment: str
    hook_type: str
    core_concept: str
    hook_line: str
    script_15s: Script
    script_30s: Script
    shot_list: list[Shot] = Field(..., min_length=8, max_length=8)
    on_screen_text: list[str] = Field(..., min_length=8, max_length=8)
    nanobanana_prompts: list[str] = Field(..., min_length=8, max_length=8)
    kling_15s: KlingPrompt
    kling_30s: KlingPrompt


class Selection(BaseModel):
    selection_seed: str = Field(..., min_length=16)
    variant_intent_strategy: str = "A_emotion_B_logic_C_offer"
