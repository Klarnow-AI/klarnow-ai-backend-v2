"""Starter brand onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import build_brand_identity_profile


@dataclass(frozen=True)
class StarterBrandStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    append_suggested_logos: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    has_starter_brand_outputs: Callable[[Any], bool]
    get_cached_fingerprint: Callable[[Any, str], str]
    resolve_brand_name: Callable[[Any], str]
    resolve_vibe_chips: Callable[[Any], list[str]]
    build_onboarding_context: Callable[[Any], str]
    iso_now: Callable[[], str]
    stage_name: str
    input_fingerprint_key: str
    normalized_artifact_type: str
    brand_os_artifact_type: str
    artifact_type: str


def run_starter_brand_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: StarterBrandStageRuntime,
):
    from app.modules.packs.logo_generation import get_logo_variant_urls
    from app.modules.packs.onboarding_services import generate_starter_brand

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = (job.get("stages") or {}).get(runtime.stage_name, {"status": "pending"})
    answers = pack.onboarding_answers or {}
    input_fingerprint = runtime.compute_input_fingerprint(pack)

    if stage["status"] == "completed" or (
        runtime.has_starter_brand_outputs(pack)
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
            data={
                "wordmark": answers.get("wordmark_svg_or_url"),
                "artifact_version": envelope.version,
            },
        )

    pack = runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
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
    result = generate_starter_brand(
        brand_name,
        vibe_chips,
        onboarding_context,
        pack_id=str(pack_id),
    )
    wordmark_to_use = result["wordmark_svg_or_url"]
    pack = runtime.append_suggested_logos(
        db,
        pack,
        get_logo_variant_urls(result) or [wordmark_to_use],
        commit=False,
    )
    runtime.merge_onboarding_answers(
        db,
        pack,
        {
            "wordmark_svg_or_url": wordmark_to_use,
            "generated_logo_url": result.get("logo_url"),
            "transparent_logo_url": result.get("transparent_logo_url"),
            "palette": result["palette"],
            "starter_brand_job_id": job_id,
            "starter_brand_completed_at": runtime.iso_now(),
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
        data={"wordmark": wordmark_to_use, "artifact_version": envelope.version},
    )
