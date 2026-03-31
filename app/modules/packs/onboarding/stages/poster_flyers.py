"""Poster flyer onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import build_creative_brief_bundle


@dataclass(frozen=True)
class PosterFlyersStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    raise_if_pause_requested: Callable[[Session, UUID, str], None]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    expected_auto_poster_names: Callable[[], list[str]]
    count_existing_auto_posters: Callable[[Session, UUID], int]
    get_cached_fingerprint: Callable[[Any, str], str]
    iso_now: Callable[[], str]
    auto_poster_queue_config: Sequence[tuple[str, str, str]]
    auto_poster_prompt: str
    collect_stream_text: Callable[[Any], str]
    parse_generated_files: Callable[[str], dict[str, str]]
    extract_poster_template_id: Callable[[str], str | None]
    build_auto_generation_messages: Callable[[str], list[dict[str, str]]]
    stage_name: str
    input_fingerprint_key: str
    website_artifact_type: str
    artifact_type: str


def _poster_prompt_from_brief(base_prompt: str, creative_brief: Any, website_blueprint: Any | None) -> str:
    parts = [base_prompt]
    if getattr(creative_brief, "campaign_objective", None):
        parts.append(f"Campaign objective: {creative_brief.campaign_objective}")
    if getattr(creative_brief, "asset_audience", None):
        parts.append(f"Audience: {creative_brief.asset_audience}")
    if getattr(creative_brief, "headline_options", None):
        parts.append("Headline options: " + " | ".join(creative_brief.headline_options[:3]))
    if getattr(creative_brief, "support_copy", None):
        parts.append("Support copy: " + " | ".join(creative_brief.support_copy[:3]))
    if getattr(creative_brief, "cta", None):
        parts.append(f"CTA: {creative_brief.cta}")
    if website_blueprint and getattr(website_blueprint, "funnel_logic", None):
        parts.append("Website funnel logic: " + " | ".join(website_blueprint.funnel_logic[:3]))
    return "\n".join(parts)


def run_poster_flyers_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: PosterFlyersStageRuntime,
):
    from app.modules.creative.generation import create_poster_generation_stream
    from app.modules.creative.services import create_asset, list_assets_for_pack
    from app.shared.generation_schemas import GenerationMessage
    from app.shared.services.generation_context import load_generation_brand_context

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    expected_names = runtime.expected_auto_poster_names()
    existing_assets = list_assets_for_pack(db, pack_id)
    existing_by_name = {
        str(asset.name): asset
        for asset in existing_assets
        if isinstance(getattr(asset, "name", None), str)
    }
    existing_auto_count = runtime.count_existing_auto_posters(db, pack_id)

    if stage["status"] == "completed" or (
        existing_auto_count >= len(expected_names)
        and runtime.get_cached_fingerprint(pack, runtime.input_fingerprint_key) == input_fingerprint
    ):
        brand_context = load_generation_brand_context(db, pack_id, pack=pack, artifacts_only=True)
        website_blueprint = runtime.get_artifact(pack, runtime.website_artifact_type)
        envelope = runtime.save_artifact(
            pack,
            runtime.artifact_type,
            build_creative_brief_bundle(
                pack,
                brand_context,
                website_blueprint,
                asset_names=sorted(existing_by_name.keys()),
            ),
            source_stage=runtime.stage_name,
            timestamp=runtime.iso_now(),
            job_id=job_id,
            input_fingerprint=input_fingerprint,
        )
        runtime.merge_onboarding_answers(
            db,
            pack,
            {
                "onboarding_poster_flyers_generated_at": runtime.iso_now(),
                runtime.input_fingerprint_key: input_fingerprint,
            },
            commit=False,
        )
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={"file_count": existing_auto_count, "artifact_version": envelope.version},
        )

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    brand_context = load_generation_brand_context(db, pack_id, pack=pack, artifacts_only=True)
    website_blueprint = runtime.get_artifact(pack, runtime.website_artifact_type)
    creative_brief = build_creative_brief_bundle(
        pack,
        brand_context,
        website_blueprint,
        asset_names=expected_names,
    )
    generation_prompt = _poster_prompt_from_brief(
        runtime.auto_poster_prompt,
        creative_brief,
        website_blueprint,
    )

    for slot_id, label, description in runtime.auto_poster_queue_config:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            f"Generating {label}: {description}.",
            stage_name=runtime.stage_name,
        )
        generated_text = runtime.collect_stream_text(
            create_poster_generation_stream(
                messages=[GenerationMessage(role="user", content=generation_prompt)],
                pack=pack,
                brand_context=brand_context,
                reference_images=[],
                generation_mode="auto",
                slot_id=slot_id,  # type: ignore[arg-type]
                existing_files=None,
            )
        )
        generated_files = runtime.parse_generated_files(generated_text)
        if not generated_files:
            raise RuntimeError(f"Poster generation for {slot_id} did not produce any files")
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            f"{label} returned {len(generated_files)} file(s).",
            stage_name=runtime.stage_name,
        )

        for name, code in generated_files.items():
            if not code.strip():
                continue
            normalized_name = name if name.startswith("/") else f"/{name}"
            if normalized_name in existing_by_name:
                continue
            asset = create_asset(
                db,
                pack_id,
                "poster",
                normalized_name,
                code,
                template_id=runtime.extract_poster_template_id(normalized_name),
                chat_messages=runtime.build_auto_generation_messages(slot_id),
            )
            existing_by_name[normalized_name] = asset
            runtime.log_job_event(
                db,
                pack_id,
                job_id,
                f"Saved {normalized_name}.",
                stage_name=runtime.stage_name,
            )

    final_auto_count = runtime.count_existing_auto_posters(db, pack_id)
    if final_auto_count < len(expected_names):
        raise RuntimeError("Poster generation completed without creating the full starter pack")

    envelope = runtime.save_artifact(
        pack,
        runtime.artifact_type,
        build_creative_brief_bundle(
            pack,
            brand_context,
            website_blueprint,
            asset_names=sorted(existing_by_name.keys()),
        ),
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    runtime.merge_onboarding_answers(
        db,
        pack,
        {
            "onboarding_poster_flyers_generated_at": runtime.iso_now(),
            runtime.input_fingerprint_key: input_fingerprint,
        },
        commit=False,
    )
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={"file_count": final_auto_count, "artifact_version": envelope.version},
    )
