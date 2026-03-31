"""Combined brand identity onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import build_brand_identity_profile


@dataclass(frozen=True)
class BrandIdentityStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    get_existing_onboarding_brand_os: Callable[..., Any]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    append_suggested_logos: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    get_cached_fingerprint: Callable[[Any, str], str]
    resolve_brand_name: Callable[[Any], str]
    resolve_vibe_chips: Callable[[Any], list[str]]
    build_onboarding_context: Callable[[Any], dict[str, Any] | None]
    extract_palette: Callable[[dict[str, Any]], dict[str, Any] | None]
    summary_text_or_none: Callable[..., str | None]
    iso_now: Callable[[], str]
    stage_name: str
    input_fingerprint_key: str
    normalized_artifact_type: str
    brand_os_artifact_type: str
    artifact_type: str


def _save_brand_identity_artifact(
    runtime: BrandIdentityStageRuntime,
    *,
    pack: Any,
    job_id: str,
    input_fingerprint: str,
):
    return runtime.save_artifact(
        pack,
        runtime.artifact_type,
        build_brand_identity_profile(
            pack,
            runtime.get_artifact(pack, runtime.normalized_artifact_type),
            runtime.get_artifact(pack, runtime.brand_os_artifact_type),
        ),
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )


def run_brand_identity_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: BrandIdentityStageRuntime,
):
    from app.modules.brand_os.services import get_active_for_pack, get_summary_fields
    from app.modules.packs.logo_generation import (
        generate_logo,
        get_logo_primary_asset_url,
        get_logo_variant_urls,
    )
    from app.modules.packs.onboarding_services import generate_starter_brand

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")

    stage = job["stages"][runtime.stage_name]
    answers = pack.onboarding_answers or {}
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    existing_artifact = runtime.get_artifact(pack, runtime.artifact_type)

    if stage["status"] == "completed" or (
        existing_artifact
        and runtime.get_cached_fingerprint(pack, runtime.input_fingerprint_key) == input_fingerprint
    ):
        envelope = _save_brand_identity_artifact(
            runtime,
            pack=pack,
            job_id=job_id,
            input_fingerprint=input_fingerprint,
        )
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={
                "artifact_version": envelope.version,
                "wordmark": answers.get("wordmark_svg_or_url"),
                "logo_url": answers.get("generated_logo_url"),
            },
        )

    pack = runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    answers = pack.onboarding_answers or {}
    is_existing_brand = answers.get("has_existing_brand") == "yes"

    if not is_existing_brand:
        brand_name = runtime.resolve_brand_name(pack)
        vibe_chips = runtime.resolve_vibe_chips(pack)
        onboarding_context = runtime.build_onboarding_context(pack)
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            f"Generating starter brand assets for {brand_name}.",
            stage_name=runtime.stage_name,
        )
        starter_brand_result = generate_starter_brand(
            brand_name,
            vibe_chips,
            onboarding_context,
            pack_id=str(pack_id),
        )
        wordmark_to_use = starter_brand_result["wordmark_svg_or_url"]
        pack = runtime.append_suggested_logos(
            db,
            pack,
            get_logo_variant_urls(starter_brand_result) or [wordmark_to_use],
            commit=False,
        )
        pack = runtime.merge_onboarding_answers(
            db,
            pack,
            {
                "wordmark_svg_or_url": wordmark_to_use,
                "generated_logo_url": starter_brand_result.get("logo_url"),
                "transparent_logo_url": starter_brand_result.get("transparent_logo_url"),
                "palette": starter_brand_result["palette"],
                "starter_brand_job_id": job_id,
                "starter_brand_completed_at": runtime.iso_now(),
            },
            commit=False,
        )

    palette = runtime.extract_palette(pack.onboarding_answers or {})
    brand_os = runtime.get_existing_onboarding_brand_os(db, pack, job_id) or get_active_for_pack(db, pack_id)
    logo_url = None
    transparent_logo_url = None

    if palette and brand_os:
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            "Generating a final logo from the approved brand palette and strategy.",
            stage_name=runtime.stage_name,
        )
        mission, vision, _ = get_summary_fields(brand_os)
        foundation = brand_os.foundation if isinstance(brand_os.foundation, dict) else {}
        summary_parts = [
            part
            for part in [
                runtime.summary_text_or_none(mission),
                runtime.summary_text_or_none(vision),
                runtime.summary_text_or_none(foundation.get("one_line_offer")),
                runtime.summary_text_or_none(foundation.get("brand_industry")),
                runtime.summary_text_or_none(foundation.get("main_audience")),
            ]
            if part
        ]
        brand_os_summary = " ".join(summary_parts)[:1500] if summary_parts else None
        logo_result = generate_logo(
            brand_name=(pack.brand_name or pack.name or "My Brand"),
            prompt="distinctive, creative logo, professional and memorable, not generic",
            pack_id=str(pack_id),
            color_scheme="use the provided palette",
            brand_os_summary=brand_os_summary,
            color_palette=palette,
            strict=False,
        )
        logo_url = str(logo_result.get("logo_url") or "").strip() or None
        transparent_logo_url = (
            str(logo_result.get("transparent_logo_url") or logo_result.get("wordmark_svg_or_url") or "").strip()
            or None
        )
        primary_logo_url = get_logo_primary_asset_url(logo_result)
        if primary_logo_url:
            pack = runtime.append_suggested_logos(
                db,
                pack,
                get_logo_variant_urls(logo_result),
                commit=False,
            )
            pack = runtime.merge_onboarding_answers(
                db,
                pack,
                {
                    "generated_logo_url": logo_url,
                    "transparent_logo_url": transparent_logo_url,
                    "wordmark_svg_or_url": primary_logo_url,
                    "final_logo_job_id": job_id,
                    "final_logo_completed_at": runtime.iso_now(),
                },
                commit=False,
            )

    pack = runtime.merge_onboarding_answers(
        db,
        pack,
        {runtime.input_fingerprint_key: input_fingerprint},
        commit=False,
    )
    envelope = _save_brand_identity_artifact(
        runtime,
        pack=pack,
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={
            "artifact_version": envelope.version,
            "wordmark": (pack.onboarding_answers or {}).get("wordmark_svg_or_url"),
            "logo_url": logo_url or (pack.onboarding_answers or {}).get("generated_logo_url"),
            "transparent_logo_url": transparent_logo_url or (pack.onboarding_answers or {}).get("transparent_logo_url"),
        },
    )
