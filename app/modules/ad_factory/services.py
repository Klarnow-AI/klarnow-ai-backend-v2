"""Ad Factory services: snapshots, compile orchestration, and compatibility payloads."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.gates import can_generate_assets
from app.modules.ad_factory.claim_guard import run_claim_guard
from app.modules.ad_factory.engines.engine0_pack_context import run as run_engine0
from app.modules.ad_factory.engines.engine1_context_builder import run as run_engine1
from app.modules.ad_factory.engines.engine2_variation_controller import run as run_engine2
from app.modules.ad_factory.engines.engine3_pattern_assembler import run as run_engine3
from app.modules.ad_factory.engines.engine4_script_converter import run as run_engine4
from app.modules.ad_factory.engines.engine5_visual_director import run as run_engine5
from app.modules.ad_factory.engines.engine6_kling_assembler import run as run_engine6
from app.modules.ad_factory.kling_adapter import build_legacy_kling_prompt
from app.modules.ad_factory.kling_client import KLING_TEXT_TO_VIDEO_MODEL
from app.modules.ad_factory.models import (
    AdFactoryCompile,
    AdFactoryRenderJob,
    COMPILE_STATUS_COMPILED,
    COMPILE_STATUS_VALIDATION_FAILED,
)
from app.modules.ad_factory.registry.data import get_versions
from app.modules.ad_factory.schemas import (
    AdFactoryCompileRead,
    AdFactoryLaunchResponse,
    BrandBrief,
    CTAResolved,
    CTADestination,
    ClaimGuardResult,
    CompiledVariant,
    CompileResultPayload,
    CompileSelection,
    LaunchRecommendation,
    LaunchState,
    LaunchStateEntry,
    LegacyGenerateResponse,
    LegacyScript,
    LegacyScriptBeat,
    LegacyShot,
    LegacyVariant,
    PackSnapshot,
    ProofAsset,
    ValidationCheck,
    ValidatorResult,
    VariantsBySlot,
    VersionBundle,
)
from app.modules.ad_factory.validation import validate_variants
from app.modules.builder.services import get_published_for_pack
from app.modules.campaign.services import get_active_for_pack
from app.modules.packs.models import Pack
from app.modules.packs.services import get_pack_for_user
from app.modules.sprint.services import get_active_sprint_for_pack

CTA_ACTION_MAP = {
    "book": ["book", "schedule", "calendar"],
    "call": ["call", "ring", "phone"],
    "dm": ["dm", "message", "slide"],
    "visit": ["visit", "go to", "click", "link"],
    "buy": ["buy", "purchase", "get it", "add to cart"],
    "whatsapp": ["whatsapp", "whats app"],
    "apply": ["apply", "join", "sign up"],
}


def _infer_cta_action(cta_text: str) -> str:
    lower = (cta_text or "").lower()
    for action, keywords in CTA_ACTION_MAP.items():
        if any(keyword in lower for keyword in keywords):
            return action
    return "visit"


def _coalesce_text(*values: object | None, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def build_brand_brief_from_pack(db: Session, pack: Pack) -> BrandBrief:
    campaign = get_active_for_pack(db, pack.id)
    site = get_published_for_pack(db, pack.id)

    cta_raw = ((campaign.primary_cta if campaign else None) or pack.primary_cta or "Visit the link").strip()
    cta_action = _infer_cta_action(cta_raw)

    if site and site.live_url:
        destination_value = site.live_url
    else:
        destination_value = pack.website_url or "https://example.com"

    location = (pack.location_city or "") + (f", {pack.location_country}" if pack.location_country else "")
    if not location.strip():
        location = "Local"

    valid_proof_types = {
        "testimonial",
        "case_study",
        "numbers",
        "screenshots",
        "before_after",
        "ugc",
        "press",
        "certification",
    }
    proof_assets: list[ProofAsset] = []
    if pack.proof_types:
        for proof_type in pack.proof_types[:5]:
            normalized = str(proof_type).lower().replace(" ", "_")
            if normalized in valid_proof_types:
                proof_assets.append(
                    ProofAsset(
                        asset_type=normalized,  # type: ignore[arg-type]
                        label=str(proof_type).replace("_", " ").title(),
                    )
                )
    if pack.proof_text and not proof_assets:
        proof_assets.append(ProofAsset(asset_type="numbers", label="Results"))

    tone = "direct"
    if pack.usp_category and "friendly" in str(pack.usp_category).lower():
        tone = "friendly"

    return BrandBrief(
        business_name=pack.brand_name or pack.name or "Business",
        offer=pack.offer_one_liner or "Our offer",
        audience=pack.target_audience or "Your audience",
        location=location,
        primary_outcome=pack.primary_outcome or "Get results",
        proof_assets=proof_assets,
        tone=tone,  # type: ignore[arg-type]
        face_on_camera=True,
        price_position="mid",
        cta_action=cta_action,  # type: ignore[arg-type]
        cta_destination=CTADestination(
            destination_type="landing_page",
            value=destination_value,
        ),
        usp=pack.usp_statement,
        core_concept=pack.core_concept,
    )


def build_pack_snapshot(db: Session, pack: Pack) -> PackSnapshot:
    sprint = get_active_sprint_for_pack(db, pack.id)
    day = sprint.current_day if sprint else 1
    sprint_id = str(sprint.id) if sprint else str(pack.id)

    if day <= 2:
        stage = "clarity"
    elif day <= 4:
        stage = "setup"
    elif day <= 7:
        stage = "publish"
    elif day <= 10:
        stage = "traffic"
    elif day <= 13:
        stage = "follow_up"
    else:
        stage = "close"

    return PackSnapshot(
        pack_id=str(pack.id),
        pack_name=pack.name or "Pack",
        sprint_id=sprint_id,
        day=max(1, day),
        stage=stage,  # type: ignore[arg-type]
        traffic_source="unknown",
    )


def _build_versions() -> VersionBundle:
    versions = get_versions()
    return VersionBundle(
        schema_version=versions["schema_version"],
        registry_version=versions["registry_version"],
        pattern_pack_version=versions["pattern_pack_version"],
        engine_logic_version=versions["engine_logic_version"],
        provider_adapter_version=versions["provider_adapter_version"],
        model_version_map={
            "kling_text_to_video_model": KLING_TEXT_TO_VIDEO_MODEL,
            "adapter": versions["provider_adapter_version"],
        },
    )


def _build_launch_recommendation() -> LaunchRecommendation:
    return LaunchRecommendation(
        order=["A", "B", "C"],
        rationale=[
            "Start with the emotion-led variant for broad initial capture.",
            "Test the logic-led variant second to pressure-test clarity and proof.",
            "Use the offer-led smash after early response confirms the offer angle.",
        ],
    )


def _build_variants(
    engine2_output,
    engine4_output,
    engine5_output,
    engine6_output,
) -> VariantsBySlot:
    variants_by_slot: dict[str, CompiledVariant] = {}
    for index, variant_plan in enumerate(engine2_output.variant_plans):
        scripts = engine4_output.scripts[index]
        shot_plan = engine5_output.shot_plans[index]
        render_intents = engine6_output.render_intents[index]
        variants_by_slot[variant_plan.slot] = CompiledVariant(
            slot=variant_plan.slot,
            intent=variant_plan.intent,
            path=variant_plan.path,
            treatment=variant_plan.treatment,
            hook_type=variant_plan.hook_type,
            core_concept=scripts.core_concept,
            hook_line=scripts.hook_line,
            hook_lineage=scripts.hook_lineage,
            script_15s=scripts.script_15s,
            script_30s=scripts.script_30s,
            anchor_shot_plan=shot_plan.anchor_shot_plan,
            on_screen_text=shot_plan.on_screen_text,
            nanobanana_prompts=shot_plan.nanobanana_prompts,
            render_intent_15s=render_intents.render_intent_15s,
            render_intent_30s=render_intents.render_intent_30s,
            cta=scripts.cta,
        )
    return VariantsBySlot(
        A=variants_by_slot["A"],
        B=variants_by_slot["B"],
        C=variants_by_slot["C"],
    )


def _compile_to_read(compile_record: AdFactoryCompile) -> AdFactoryCompileRead:
    return AdFactoryCompileRead.model_validate(
        {
            "id": compile_record.id,
            "pack_id": compile_record.pack_id,
            "status": compile_record.status,
            "brand_brief": compile_record.brand_brief_snapshot,
            "pack_snapshot": compile_record.pack_snapshot,
            "selection": compile_record.selection,
            "versions": compile_record.versions,
            "compile_result": compile_record.compile_result,
            "claim_guard_result": compile_record.claim_guard_result,
            "validator_result": compile_record.validator_result,
            "launch_recommendation": compile_record.launch_recommendation,
            "launch_state": compile_record.launch_state,
            "created_at": compile_record.created_at,
            "updated_at": compile_record.updated_at,
        }
    )


def generate_compile(
    db: Session,
    pack_id: UUID,
    user_id: UUID,
    *,
    selection_seed: str | None = None,
) -> AdFactoryCompileRead:
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise ValueError("Pack not found")
    can_generate_assets(db, pack)

    brand_brief = build_brand_brief_from_pack(db, pack)
    pack_snapshot = build_pack_snapshot(db, pack)
    selection = CompileSelection(
        selection_seed=selection_seed or secrets.token_hex(16),
    )
    versions = _build_versions()

    # Release the initial read transaction before the in-memory compile pass.
    db.rollback()

    engine0 = run_engine0(pack_snapshot, brand_brief)
    engine1 = run_engine1(brand_brief, engine0, selection.selection_seed)
    engine2 = run_engine2(brand_brief, engine1, selection.selection_seed)
    engine3 = run_engine3(
        brand_brief,
        engine0,
        engine2,
        engine1.proof_strategy_candidate.strategy_id,
        selection.selection_seed,
    )
    engine4 = run_engine4(brand_brief, engine2, engine3)
    engine5 = run_engine5(brand_brief, engine3, engine4)
    engine6 = run_engine6(brand_brief, engine2, engine4, engine5)
    variants = _build_variants(engine2, engine4, engine5, engine6)
    claim_guard_result = run_claim_guard(variants)
    validator_result = validate_variants(brand_brief, variants, claim_guard_result)

    compile_result = CompileResultPayload(
        engine0_output=engine0,
        engine1_output=engine1,
        engine2_output=engine2,
        engine3_output=engine3,
        engine4_output=engine4,
        engine5_output=engine5,
        engine6_output=engine6,
        variants=variants,
    )
    compile_record = AdFactoryCompile(
        pack_id=pack_id,
        status=(
            COMPILE_STATUS_COMPILED
            if validator_result.status == "pass"
            else COMPILE_STATUS_VALIDATION_FAILED
        ),
        brand_brief_snapshot=brand_brief.model_dump(mode="json"),
        pack_snapshot=pack_snapshot.model_dump(mode="json"),
        selection=selection.model_dump(mode="json"),
        versions=versions.model_dump(mode="json"),
        compile_result=compile_result.model_dump(mode="json"),
        claim_guard_result=claim_guard_result.model_dump(mode="json"),
        validator_result=validator_result.model_dump(mode="json"),
        launch_recommendation=_build_launch_recommendation().model_dump(mode="json"),
        launch_state=LaunchState().model_dump(mode="json"),
    )
    db.add(compile_record)
    db.commit()
    db.refresh(compile_record)
    return _compile_to_read(compile_record)


def get_compile(db: Session, compile_id: UUID, user_id: UUID) -> AdFactoryCompile | None:
    return (
        db.query(AdFactoryCompile)
        .join(Pack, Pack.id == AdFactoryCompile.pack_id)
        .filter(
            AdFactoryCompile.id == compile_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )


def get_render_job(db: Session, render_job_id: UUID, user_id: UUID) -> AdFactoryRenderJob | None:
    return (
        db.query(AdFactoryRenderJob)
        .join(Pack, Pack.id == AdFactoryRenderJob.pack_id)
        .filter(
            AdFactoryRenderJob.id == render_job_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )


def read_compile(db: Session, compile_id: UUID, user_id: UUID) -> AdFactoryCompileRead | None:
    compile_record = get_compile(db, compile_id, user_id)
    if not compile_record:
        return None
    return _compile_to_read(compile_record)


def mark_variant_live(
    db: Session,
    compile_id: UUID,
    user_id: UUID,
    slot: str,
) -> AdFactoryLaunchResponse:
    compile_record = get_compile(db, compile_id, user_id)
    if not compile_record:
        raise ValueError("Compile result not found")
    if slot not in {"A", "B", "C"}:
        raise ValueError("Variant slot must be A, B, or C")

    launch_state = LaunchState.model_validate(compile_record.launch_state or {})
    if all(entry.slot != slot for entry in launch_state.live_order):
        launch_state.live_order.append(
            LaunchStateEntry(
                slot=slot,  # type: ignore[arg-type]
                marked_live_at=datetime.now(timezone.utc),
            )
        )
        compile_record.launch_state = launch_state.model_dump(mode="json")
        db.commit()
        db.refresh(compile_record)

    return AdFactoryLaunchResponse(
        compile_id=compile_record.id,
        slot=slot,  # type: ignore[arg-type]
        launch_state=LaunchState.model_validate(compile_record.launch_state or {}),
    )


def _legacy_script(script) -> LegacyScript:
    return LegacyScript(
        beats=[
            LegacyScriptBeat(beat_name=beat.beat_name, text=beat.text)
            for beat in script.beats
        ],
        timing_rules_satisfied=script.timing_rules_satisfied,
    )


def _legacy_variant(variant: CompiledVariant) -> LegacyVariant:
    return LegacyVariant(
        slot=variant.slot,
        intent=variant.intent,
        path=variant.path,
        treatment=variant.treatment,
        hook_type=variant.hook_type,
        core_concept=variant.core_concept,
        hook_line=variant.hook_line,
        script_15s=_legacy_script(variant.script_15s),
        script_30s=_legacy_script(variant.script_30s),
        shot_list=[
            LegacyShot(
                shot_type=shot.shot_type,
                description=shot.description,
                on_screen_text=shot.on_screen_text,
                nanobanana_prompt=shot.nanobanana_prompt,
            )
            for shot in variant.anchor_shot_plan
        ],
        on_screen_text=[item.text for item in variant.on_screen_text],
        nanobanana_prompts=[item.text for item in variant.nanobanana_prompts],
        kling_15s=build_legacy_kling_prompt(variant.render_intent_15s),
        kling_30s=build_legacy_kling_prompt(variant.render_intent_30s),
    )


def build_legacy_generate_response(compile_read: AdFactoryCompileRead) -> LegacyGenerateResponse:
    variants = compile_read.compile_result.variants
    return LegacyGenerateResponse(
        render_id=str(compile_read.id),
        compile_id=compile_read.id,
        variants=[
            _legacy_variant(variants.A),
            _legacy_variant(variants.B),
            _legacy_variant(variants.C),
        ],
        validation_status=compile_read.validator_result.status,
        validation_checks=compile_read.validator_result.checks,
    )
