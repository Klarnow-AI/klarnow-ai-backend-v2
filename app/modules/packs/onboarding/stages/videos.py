"""Video onboarding stage implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import (
    build_video_brief_bundle,
    build_video_render_result,
)


def _video_assets(assets: list[Any]) -> list[Any]:
    return [asset for asset in assets if getattr(asset, "type", None) == "video"]


@dataclass(frozen=True)
class VideoBriefsStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    get_cached_fingerprint: Callable[[Any, str], str]
    iso_now: Callable[[], str]
    auto_video_count: int
    stage_name: str
    input_fingerprint_key: str
    website_artifact_type: str
    creative_artifact_type: str
    artifact_type: str


@dataclass(frozen=True)
class VideoRenderStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    get_cached_fingerprint: Callable[[Any, str], str]
    iso_now: Callable[[], str]
    auto_video_count: int
    stage_name: str
    input_fingerprint_key: str
    brief_artifact_type: str
    artifact_type: str


def run_video_briefs_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: VideoBriefsStageRuntime,
):
    from app.modules.creative.services import list_assets_for_pack
    from app.shared.services.generation_context import load_generation_brand_context

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")

    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    existing_assets = list_assets_for_pack(db, pack_id)
    existing_video_assets = _video_assets(existing_assets)
    existing_brief = runtime.get_artifact(pack, runtime.artifact_type)

    brand_context = load_generation_brand_context(db, pack_id, pack=pack, artifacts_only=True)
    website_blueprint = runtime.get_artifact(pack, runtime.website_artifact_type)
    creative_brief = runtime.get_artifact(pack, runtime.creative_artifact_type)
    video_brief = build_video_brief_bundle(
        pack,
        brand_context,
        creative_brief,
        website_blueprint,
        count=runtime.auto_video_count,
        asset_ids=[str(getattr(asset, "id", "") or "") for asset in existing_video_assets],
    )

    if stage["status"] != "completed" and not (
        existing_brief and runtime.get_cached_fingerprint(pack, runtime.input_fingerprint_key) == input_fingerprint
    ):
        runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            f"Prepared {len(video_brief.voiceover_script)} starter video brief(s).",
            stage_name=runtime.stage_name,
        )

    envelope = runtime.save_artifact(
        pack,
        runtime.artifact_type,
        video_brief,
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    runtime.merge_onboarding_answers(
        db,
        pack,
        {
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
        data={
            "script_count": len(video_brief.voiceover_script),
            "artifact_version": envelope.version,
        },
    )


def run_video_render_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: VideoRenderStageRuntime,
):
    from app.modules.creative.services import list_assets_for_pack
    from app.modules.creative.tools import render_video

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")

    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    video_brief = runtime.get_artifact(pack, runtime.brief_artifact_type)
    if not video_brief:
        raise RuntimeError("Video brief artifact is missing. Run video_briefs first.")

    existing_assets = list_assets_for_pack(db, pack_id)
    existing_video_assets = _video_assets(existing_assets)
    existing_video_count = len(existing_video_assets)
    requested_count = max(
        runtime.auto_video_count,
        len(getattr(video_brief, "voiceover_script", []) or []),
    )

    if stage["status"] == "completed" or (
        existing_video_count >= runtime.auto_video_count
        and runtime.get_cached_fingerprint(pack, runtime.input_fingerprint_key) == input_fingerprint
    ):
        render_result = build_video_render_result(
            existing_video_assets,
            requested_count=requested_count,
            end_frame_cta=getattr(video_brief, "end_frame_cta", None),
        )
        envelope = runtime.save_artifact(
            pack,
            runtime.artifact_type,
            render_result,
            source_stage=runtime.stage_name,
            timestamp=runtime.iso_now(),
            job_id=job_id,
            input_fingerprint=input_fingerprint,
        )
        runtime.merge_onboarding_answers(
            db,
            pack,
            {
                "onboarding_videos_generated_at": runtime.iso_now(),
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
            data={
                "video_count": existing_video_count,
                "artifact_version": envelope.version,
                "requested_count": render_result.requested_count,
            },
        )

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    missing_scripts = list(getattr(video_brief, "voiceover_script", []) or [])[existing_video_count:runtime.auto_video_count]
    if missing_scripts:
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            f"Requesting {len(missing_scripts)} starter video render(s).",
            stage_name=runtime.stage_name,
        )
        for script in missing_scripts:
            render_video(db=db, pack_id=pack.id, script=script, count=1)

    final_assets = list_assets_for_pack(db, pack_id)
    final_video_assets = _video_assets(final_assets)
    final_video_count = len(final_video_assets)
    if final_video_count <= 0:
        raise RuntimeError("Video rendering did not create any starter videos")
    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        f"Starter video count is now {final_video_count}.",
        stage_name=runtime.stage_name,
    )

    render_result = build_video_render_result(
        final_video_assets,
        requested_count=requested_count,
        end_frame_cta=getattr(video_brief, "end_frame_cta", None),
    )
    envelope = runtime.save_artifact(
        pack,
        runtime.artifact_type,
        render_result,
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    runtime.merge_onboarding_answers(
        db,
        pack,
        {
            "onboarding_videos_generated_at": runtime.iso_now(),
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
        data={
            "video_count": final_video_count,
            "artifact_version": envelope.version,
            "requested_count": render_result.requested_count,
        },
    )
