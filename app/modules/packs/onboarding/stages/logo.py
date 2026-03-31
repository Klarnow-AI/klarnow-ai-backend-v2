"""Final logo onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import build_brand_identity_profile


@dataclass(frozen=True)
class LogoStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    get_existing_onboarding_brand_os: Callable[..., Any]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    append_suggested_logos: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    has_final_logo_output: Callable[[Any], bool]
    get_cached_fingerprint: Callable[[Any, str], str]
    extract_palette: Callable[[dict[str, Any]], dict[str, Any] | None]
    summary_text_or_none: Callable[..., str | None]
    iso_now: Callable[[], str]
    stage_name: str
    input_fingerprint_key: str
    normalized_artifact_type: str
    brand_os_artifact_type: str
    artifact_type: str


def run_logo_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: LogoStageRuntime,
):
    from app.modules.brand_os.services import get_active_for_pack, get_summary_fields
    from app.modules.packs.logo_generation import (
        generate_logo,
        get_logo_primary_asset_url,
        get_logo_variant_urls,
    )

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = (job.get("stages") or {}).get(runtime.stage_name, {"status": "pending"})
    input_fingerprint = runtime.compute_input_fingerprint(pack)

    if stage["status"] == "skipped":
        return pack
    if stage["status"] == "completed" or (
        runtime.has_final_logo_output(pack)
        and runtime.get_cached_fingerprint(pack, runtime.input_fingerprint_key) == input_fingerprint
    ):
        envelope = runtime.save_artifact(
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
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={"artifact_version": envelope.version},
        )

    palette = runtime.extract_palette(pack.onboarding_answers or {})
    brand_os = runtime.get_existing_onboarding_brand_os(db, pack, job_id) or get_active_for_pack(db, pack_id)
    if not palette or not brand_os:
        return runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "skipped")

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        "Generating a final logo from the approved brand palette and strategy.",
        stage_name=runtime.stage_name,
    )
    mission, vision, _ = get_summary_fields(brand_os)
    foundation = brand_os.foundation if isinstance(brand_os.foundation, dict) else {}
    mission_text = runtime.summary_text_or_none(mission)
    vision_text = runtime.summary_text_or_none(vision)
    one_line = runtime.summary_text_or_none(foundation.get("one_line_offer"))
    industry = runtime.summary_text_or_none(foundation.get("brand_industry"))
    audience = runtime.summary_text_or_none(foundation.get("main_audience"))
    summary_parts = [part for part in [mission_text, vision_text, one_line, industry, audience] if part]
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
    if not primary_logo_url:
        return runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "skipped")

    pack = runtime.append_suggested_logos(
        db,
        pack,
        get_logo_variant_urls(logo_result),
        commit=False,
    )
    runtime.merge_onboarding_answers(
        db,
        pack,
        {
            "generated_logo_url": logo_url,
            "transparent_logo_url": transparent_logo_url,
            "wordmark_svg_or_url": primary_logo_url,
            "final_logo_job_id": job_id,
            "final_logo_completed_at": runtime.iso_now(),
            runtime.input_fingerprint_key: input_fingerprint,
        },
        commit=False,
    )
    envelope = runtime.save_artifact(
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
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={
            "logo_url": logo_url,
            "transparent_logo_url": transparent_logo_url,
            "artifact_version": envelope.version,
        },
    )
