"""Ad Factory V2.1 schemas and API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


VariantSlot = Literal["A", "B", "C"]
ScriptBeatName = Literal["hook", "problem", "mechanism", "proof", "offer", "cta"]
RenderScope = Literal["single_variant_30", "abc_bundle_30", "abc_bundle_30_plus_15"]
CompileStatus = Literal["compiled", "validation_failed", "failed"]
RenderJobStatus = Literal["pending", "reserved", "rendering", "complete", "failed"]


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


class VersionBundle(BaseModel):
    schema_version: str = Field(..., min_length=1, max_length=64)
    registry_version: str = Field(..., min_length=1, max_length=64)
    pattern_pack_version: str = Field(..., min_length=1, max_length=64)
    engine_logic_version: str = Field(..., min_length=1, max_length=64)
    provider_adapter_version: str = Field(..., min_length=1, max_length=64)
    model_version_map: dict[str, str] = Field(default_factory=dict)


class CompileSelection(BaseModel):
    selection_seed: str = Field(..., min_length=16, max_length=128)
    variant_intent_strategy: str = Field(default="A_emotion_B_logic_C_offer", min_length=3)


class Lineage(BaseModel):
    source_registry_item_id: str = Field(..., min_length=1, max_length=128)
    source_registry_item_type: str = Field(..., min_length=1, max_length=64)
    template_id: str = Field(..., min_length=1, max_length=128)
    fill_variables: dict[str, str] = Field(default_factory=dict)
    registry_version: str = Field(..., min_length=1, max_length=64)
    engine_logic_version: str = Field(..., min_length=1, max_length=64)
    generator_stage: str = Field(..., min_length=1, max_length=64)


class TimedScriptBeat(BaseModel):
    beat_name: ScriptBeatName
    text: str = Field(..., min_length=1, max_length=320)
    start_second: float = Field(..., ge=0)
    end_second: float = Field(..., ge=0)
    lineage: Lineage


class Script(BaseModel):
    beats: list[TimedScriptBeat] = Field(..., min_length=6, max_length=6)
    timing_rules_satisfied: bool


class CTAResolved(BaseModel):
    cta_action: str = Field(..., min_length=1, max_length=64)
    destination_type: str = Field(..., min_length=1, max_length=64)
    destination_value: str = Field(..., min_length=3, max_length=2048)
    mid_line: str = Field(..., min_length=1, max_length=140)
    end_line: str = Field(..., min_length=1, max_length=140)
    mid_lineage: Lineage
    end_lineage: Lineage


class LineageTextItem(BaseModel):
    text: str = Field(..., min_length=1, max_length=800)
    lineage: Lineage


class AnchorShot(BaseModel):
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
    lineage: Lineage
    caption_overlay: dict[str, Any] = Field(
        default_factory=lambda: {"enabled": True},
    )


class RenderAnchorFrame(BaseModel):
    index: int = Field(..., ge=1, le=8)
    shot_type: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=200)
    on_screen_text: str = Field(..., min_length=1, max_length=60)


class ProviderNeutralRenderIntent(BaseModel):
    duration_seconds: Literal[15, 30]
    aspect_ratio: Literal["9:16"]
    treatment: str = Field(..., min_length=1, max_length=64)
    pacing_mode: str = Field(..., min_length=1, max_length=64)
    captions_on: bool = True
    fast_cuts: bool = True
    cta_mid_and_end: bool = True
    anchor_frames: list[RenderAnchorFrame] = Field(..., min_length=5, max_length=8)
    continuity_requirements: dict[str, Any] = Field(default_factory=dict)
    voiceover_mode: Literal["native_audio", "silent"]
    provider_target: Literal["kling"]
    spoken_narration: str = Field(..., min_length=1, max_length=1000)
    caption_lines: list[str] = Field(..., min_length=5, max_length=8)
    hook_line: str = Field(..., min_length=1, max_length=60)
    core_concept: str = Field(..., min_length=1, max_length=60)
    cta_line: str = Field(..., min_length=1, max_length=140)
    business_name: str = Field(..., min_length=1, max_length=120)
    offer: str = Field(..., min_length=1, max_length=240)
    audience: str = Field(..., min_length=1, max_length=180)
    primary_outcome: str = Field(..., min_length=1, max_length=180)
    proof_line: str = Field(..., min_length=1, max_length=180)


class Engine0PackContextOutput(BaseModel):
    objective_type: Literal["lead_gen", "booking", "purchase"]
    funnel_stage: Literal["cold", "warm", "hot", "retargeting"]
    awareness_level: Literal["unaware", "problem_aware", "solution_aware", "offer_aware"]
    traffic_source: str = Field(default="unknown", max_length=32)


class ProofStrategyCandidate(BaseModel):
    strategy_id: str = Field(..., min_length=1, max_length=64)
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
    proof_strategy_candidate: ProofStrategyCandidate
    messaging_constraints: MessagingConstraints


class VariantPlan(BaseModel):
    slot: VariantSlot
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
    slot: VariantSlot
    pattern_id: str = Field(..., min_length=1, max_length=128)
    hook_id: str = Field(..., min_length=1, max_length=128)
    proof_strategy_id: str = Field(..., min_length=1, max_length=128)
    cta_id: str = Field(..., min_length=1, max_length=128)
    line_template_ids: dict[str, list[str]]
    registry_version: str = Field(..., min_length=1, max_length=64)
    pattern_pack_version: str = Field(..., min_length=1, max_length=64)


class Engine3PatternAssemblerOutput(BaseModel):
    selections: list[PatternSelection] = Field(..., min_length=3, max_length=3)


class VariantScripts(BaseModel):
    slot: VariantSlot
    core_concept: str = Field(..., max_length=60)
    hook_line: str = Field(..., max_length=60)
    hook_lineage: Lineage
    script_15s: Script
    script_30s: Script
    cta: CTAResolved


class Engine4ScriptConverterOutput(BaseModel):
    scripts: list[VariantScripts] = Field(..., min_length=3, max_length=3)


class VariantShotPlan(BaseModel):
    slot: VariantSlot
    anchor_shot_plan: list[AnchorShot] = Field(..., min_length=8, max_length=8)
    pacing: dict[str, Any]
    on_screen_text: list[LineageTextItem] = Field(..., min_length=8, max_length=8)
    nanobanana_prompts: list[LineageTextItem] = Field(..., min_length=8, max_length=8)


class Engine5VisualDirectorOutput(BaseModel):
    shot_plans: list[VariantShotPlan] = Field(..., min_length=3, max_length=3)


class VariantRenderIntents(BaseModel):
    slot: VariantSlot
    render_intent_15s: ProviderNeutralRenderIntent
    render_intent_30s: ProviderNeutralRenderIntent
    render_requirements: dict[str, Any]


class Engine6RenderAssemblerOutput(BaseModel):
    render_intents: list[VariantRenderIntents] = Field(..., min_length=3, max_length=3)


class CompiledVariant(BaseModel):
    slot: VariantSlot
    intent: Literal["emotion_led", "logic_led", "offer_led"]
    path: str
    treatment: str
    hook_type: str
    core_concept: str
    hook_line: str
    hook_lineage: Lineage
    script_15s: Script
    script_30s: Script
    anchor_shot_plan: list[AnchorShot] = Field(..., min_length=8, max_length=8)
    on_screen_text: list[LineageTextItem] = Field(..., min_length=8, max_length=8)
    nanobanana_prompts: list[LineageTextItem] = Field(..., min_length=8, max_length=8)
    render_intent_15s: ProviderNeutralRenderIntent
    render_intent_30s: ProviderNeutralRenderIntent
    cta: CTAResolved


class VariantsBySlot(BaseModel):
    A: CompiledVariant
    B: CompiledVariant
    C: CompiledVariant

    def as_dict(self) -> dict[VariantSlot, CompiledVariant]:
        return {"A": self.A, "B": self.B, "C": self.C}


class ClaimGuardCheck(BaseModel):
    rule_id: str = Field(..., min_length=1, max_length=128)
    passed: bool
    blocking: bool = True
    slot: VariantSlot | None = None
    field_path: str = Field(..., min_length=1, max_length=256)
    message: str | None = Field(None, max_length=400)


class ClaimGuardResult(BaseModel):
    status: Literal["pass", "fail"]
    checks: list[ClaimGuardCheck] = Field(default_factory=list)
    blocking_errors: list[ClaimGuardCheck] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    check_id: str = Field(..., min_length=1, max_length=128)
    passed: bool
    blocking: bool = True
    slot: VariantSlot | None = None
    field_path: str = Field(..., min_length=1, max_length=256)
    message: str | None = Field(None, max_length=400)


class ValidatorResult(BaseModel):
    status: Literal["pass", "fail"]
    checks: list[ValidationCheck] = Field(default_factory=list)
    blocking_errors: list[ValidationCheck] = Field(default_factory=list)


class LaunchRecommendation(BaseModel):
    order: list[VariantSlot] = Field(default_factory=lambda: ["A", "B", "C"])
    rationale: list[str] = Field(default_factory=list)


class LaunchStateEntry(BaseModel):
    slot: VariantSlot
    marked_live_at: datetime


class LaunchState(BaseModel):
    live_order: list[LaunchStateEntry] = Field(default_factory=list)


class CompileRequestMeta(BaseModel):
    pack_id: UUID


class AdFactoryCompileRequest(BaseModel):
    meta: CompileRequestMeta
    selection_seed: str | None = Field(None, min_length=16, max_length=128)


class CompileResultPayload(BaseModel):
    engine0_output: Engine0PackContextOutput
    engine1_output: Engine1ContextBuilderOutput
    engine2_output: Engine2VariationControllerOutput
    engine3_output: Engine3PatternAssemblerOutput
    engine4_output: Engine4ScriptConverterOutput
    engine5_output: Engine5VisualDirectorOutput
    engine6_output: Engine6RenderAssemblerOutput
    variants: VariantsBySlot


class AdFactoryCompileRead(BaseModel):
    id: UUID
    pack_id: UUID
    status: CompileStatus
    brand_brief: BrandBrief
    pack_snapshot: PackSnapshot
    selection: CompileSelection
    versions: VersionBundle
    compile_result: CompileResultPayload
    claim_guard_result: ClaimGuardResult
    validator_result: ValidatorResult
    launch_recommendation: LaunchRecommendation
    launch_state: LaunchState
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BillingSnapshot(BaseModel):
    billing_mode: Literal["disabled", "feature_flagged", "enforced"]
    render_scope: RenderScope
    credits_required: int = Field(..., ge=0)
    credits_available: int = Field(..., ge=0)
    credits_reserved: int = Field(..., ge=0)
    credits_consumed: int = Field(..., ge=0)
    purchase_required: bool = False
    reservation_expires_at: datetime | None = None
    idempotency_key: str = Field(..., min_length=8, max_length=128)


class RenderRequestPayload(BaseModel):
    compile_result_id: UUID
    selected_variants: list[VariantSlot] = Field(..., min_length=1, max_length=3)
    durations_requested: list[Literal[15, 30]] = Field(..., min_length=1, max_length=2)
    voiceover_addon: bool = False
    provider_target: Literal["kling"] = "kling"
    billing_snapshot: BillingSnapshot | None = None
    idempotency_key: str | None = Field(None, min_length=8, max_length=128)


class AdFactoryRenderJobRead(BaseModel):
    id: UUID
    compile_result_id: UUID
    pack_id: UUID
    status: RenderJobStatus
    selected_variants: list[VariantSlot]
    durations_requested: list[Literal[15, 30]]
    voiceover_addon: bool
    provider_target: str
    provider_adapter_version: str
    billing_snapshot: BillingSnapshot
    provider_job_ids: dict[str, str] = Field(default_factory=dict)
    asset_urls: dict[str, str | None] = Field(default_factory=dict)
    retry_state: dict[str, Any] = Field(default_factory=dict)
    failure_state: dict[str, Any] = Field(default_factory=dict)
    render_result: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdFactoryLaunchResponse(BaseModel):
    compile_id: UUID
    slot: VariantSlot
    launch_state: LaunchState


class LegacyScriptBeat(BaseModel):
    beat_name: str
    text: str


class LegacyScript(BaseModel):
    beats: list[LegacyScriptBeat]
    timing_rules_satisfied: bool


class LegacyShot(BaseModel):
    shot_type: str
    description: str
    on_screen_text: str
    nanobanana_prompt: str


class LegacyVariant(BaseModel):
    slot: VariantSlot
    intent: str
    path: str
    treatment: str
    hook_type: str
    core_concept: str
    hook_line: str
    script_15s: LegacyScript
    script_30s: LegacyScript
    shot_list: list[LegacyShot]
    on_screen_text: list[str]
    nanobanana_prompts: list[str]
    kling_15s: dict[str, Any]
    kling_30s: dict[str, Any]


class LegacyGenerateResponse(BaseModel):
    render_id: str
    compile_id: UUID
    variants: list[LegacyVariant]
    validation_status: Literal["pass", "fail"]
    validation_checks: list[ValidationCheck]


class LegacyRenderResponse(BaseModel):
    asset_ids: list[str]
    assets: list[dict[str, Any]]
    render_job_id: UUID
