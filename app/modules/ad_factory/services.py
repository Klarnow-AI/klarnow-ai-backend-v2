"""Ad Factory V2 services: BrandBrief resolution, pipeline orchestration."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.gates import can_generate_assets
from app.modules.ad_factory.engines.engine0_pack_context import run as run_engine0
from app.modules.ad_factory.engines.engine1_context_builder import run as run_engine1
from app.modules.ad_factory.engines.engine2_variation_controller import run as run_engine2
from app.modules.ad_factory.engines.engine3_pattern_assembler import run as run_engine3
from app.modules.ad_factory.engines.engine4_script_converter import run as run_engine4
from app.modules.ad_factory.engines.engine5_visual_director import run as run_engine5
from app.modules.ad_factory.engines.engine6_kling_assembler import run as run_engine6
from app.modules.ad_factory.models import AdFactoryRender, RENDER_STATUS_DRAFT, RENDER_STATUS_VALIDATED
from app.modules.ad_factory.schemas import BrandBrief, CTADestination, PackSnapshot, ProofAsset, Variant
from app.modules.ad_factory.validation import validate_variants
from app.modules.campaign.services import get_active_for_pack
from app.modules.builder.services import get_published_for_pack
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
        if any(kw in lower for kw in keywords):
            return action
    return "visit"


def build_brand_brief_from_pack(db: Session, pack: Pack) -> BrandBrief:
    campaign = get_active_for_pack(db, pack.id)
    site = get_published_for_pack(db, pack.id)

    cta_raw = ((campaign.primary_cta if campaign else None) or pack.primary_cta or "Visit the link").strip()
    cta_action = _infer_cta_action(cta_raw)

    destination_value = ""
    destination_type = "landing_page"
    if site and site.live_url:
        destination_value = site.live_url
    else:
        destination_value = pack.website_url or "https://example.com"

    location = (pack.location_city or "") + (f", {pack.location_country}" if pack.location_country else "")
    if not location.strip():
        location = "Local"

    valid_proof_types = (
        "testimonial", "case_study", "numbers", "screenshots",
        "before_after", "ugc", "press", "certification",
    )
    proof_assets: list[ProofAsset] = []
    if pack.proof_types:
        for pt in pack.proof_types[:5]:
            t = str(pt).lower().replace(" ", "_")
            if t in valid_proof_types:
                label = (pt if isinstance(pt, str) else t).replace("_", " ").title()
                proof_assets.append(ProofAsset(asset_type=t, label=label))
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
        tone=tone,
        face_on_camera=True,
        price_position="mid",
        cta_action=cta_action,
        cta_destination=CTADestination(destination_type=destination_type, value=destination_value),
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
        stage=stage,
        traffic_source="unknown",
    )


def generate_variants(db: Session, pack_id: UUID, user_id: UUID) -> dict:
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise ValueError("Pack not found")
    can_generate_assets(db, pack)

    brand_brief = build_brand_brief_from_pack(db, pack)
    pack_snapshot = build_pack_snapshot(db, pack)
    selection_seed = secrets.token_hex(16)

    # Release the read transaction before the in-memory generation pipeline runs so
    # the final insert uses a fresh pooled connection instead of an idle one held
    # since the initial pack lookup.
    db.rollback()

    engine0 = run_engine0(pack_snapshot)
    engine1 = run_engine1(brand_brief, engine0)
    engine2 = run_engine2(brand_brief, engine1, selection_seed)
    engine3 = run_engine3(brand_brief, engine2, engine1.proof_strategy.strategy_id, selection_seed)
    engine4 = run_engine4(brand_brief, engine2, engine3)
    engine5 = run_engine5(brand_brief, engine2, engine4)
    engine6 = run_engine6(brand_brief, engine2, engine4, engine5)

    engines_output = {
        "engine0_packContext": engine0.model_dump(),
        "engine1_contextBuilder": engine1.model_dump(),
        "engine2_variationController": engine2.model_dump(),
        "engine3_patternAssembler": engine3.model_dump(),
        "engine4_scriptConverter": engine4.model_dump(),
        "engine5_visualDirector": engine5.model_dump(),
        "engine6_klingAssembler": engine6.model_dump(),
    }

    variants_data: list[dict] = []
    for i, vp in enumerate(engine2.variant_plans):
        scripts = engine4.scripts[i]
        shot_plan = engine5.shot_plans[i]
        kling = engine6.kling_prompts[i]
        v = Variant(
            slot=vp.slot,
            intent=vp.intent,
            path=vp.path,
            treatment=vp.treatment,
            hook_type=vp.hook_type,
            core_concept=scripts.core_concept,
            hook_line=scripts.hook_line,
            script_15s=scripts.script_15s,
            script_30s=scripts.script_30s,
            shot_list=shot_plan.shots,
            on_screen_text=[s.on_screen_text for s in shot_plan.shots],
            nanobanana_prompts=[s.nanobanana_prompt for s in shot_plan.shots],
            kling_15s=kling.kling_15s,
            kling_30s=kling.kling_30s,
        )
        variants_data.append(v.model_dump())

    passed, checks = validate_variants(brand_brief, [Variant(**d) for d in variants_data])

    render = AdFactoryRender(
        pack_id=pack_id,
        status=RENDER_STATUS_VALIDATED if passed else RENDER_STATUS_DRAFT,
        brand_brief_snapshot=brand_brief.model_dump(),
        pack_snapshot=pack_snapshot.model_dump(),
        selection_seed=selection_seed,
        pattern_ids_used=[s.pattern_id for s in engine3.selections],
        hook_ids_used=[s.hook_id for s in engine3.selections],
        proof_strategy_id=engine1.proof_strategy.strategy_id,
        cta_id=engine3.selections[0].cta_id if engine3.selections else None,
        engines_output=engines_output,
        variants=variants_data,
        render_metadata={
            "validation_passed": passed,
            "validation_checks": checks,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(render)
    db.commit()

    return {
        "render_id": str(render.id),
        "variants": variants_data,
        "validation_status": "pass" if passed else "fail",
        "validation_checks": checks,
    }


def get_render(db: Session, render_id: UUID, user_id: UUID) -> AdFactoryRender | None:
    return (
        db.query(AdFactoryRender)
        .join(Pack, Pack.id == AdFactoryRender.pack_id)
        .filter(
            AdFactoryRender.id == render_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )
