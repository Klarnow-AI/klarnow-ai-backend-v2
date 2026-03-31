"""Onboarding job orchestration service."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db.observability import (
    get_db_query_count,
    get_db_query_duration_ms,
    reset_db_query_stats,
)
from app.core.errors import DomainNotFoundError
from app.core.db.session import SessionLocal
from app.modules.packs.models import Pack, utc_now
from app.modules.packs.onboarding.artifact_store import (
    get_artifact as _get_artifact,
    get_artifact_envelope as _get_artifact_envelope,
    get_artifact_versions as _get_artifact_versions,
    save_artifact as _save_artifact,
)
from app.modules.packs.onboarding.artifacts import (
    ARTIFACT_TYPE_BRAND_OS,
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
    ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
    ARTIFACT_TYPE_QA_REPORT,
    ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_RENDER_RESULT,
    ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
)
from app.modules.packs.onboarding.common import (
    OnboardingPauseRequested,
    OnboardingRunResult,
    _iso_now,
    _summary_text_or_none,
    _text_or_none,
)
from app.modules.packs.onboarding.constants import (
    ACTIVE_ONBOARDING_JOB_STATUSES,
    BRAND_IDENTITY_INPUT_FINGERPRINT_KEY,
    BRAND_OS_INPUT_FINGERPRINT_KEY,
    LOGO_INPUT_FINGERPRINT_KEY,
    NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY,
    ONBOARDING_JOB_STAGES,
    ONBOARDING_JOB_KEY,
    ONBOARDING_JOB_MAX_ATTEMPTS,
    POSTER_FLYERS_INPUT_FINGERPRINT_KEY,
    PUBLIC_STAGE_BRAND_IDENTITY,
    PUBLIC_STAGE_BRAND_OS,
    PUBLIC_STAGE_POSTER_FLYERS,
    PUBLIC_STAGE_VIDEOS,
    PUBLIC_STAGE_WEBSITE,
    STAGE_BRAND_IDENTITY,
    STAGE_BRAND_OS,
    STAGE_LOGO,
    STAGE_NORMALIZE_INPUT,
    STAGE_POSTER_FLYERS,
    STAGE_QA_REVIEW,
    STAGE_STARTER_BRAND,
    STAGE_VIDEO_BRIEFS,
    STAGE_VIDEO_RENDER,
    STAGE_WEBSITE,
    QA_REVIEW_INPUT_FINGERPRINT_KEY,
    STARTER_BRAND_INPUT_FINGERPRINT_KEY,
    VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY,
    VIDEO_RENDER_INPUT_FINGERPRINT_KEY,
    WEBSITE_INPUT_FINGERPRINT_KEY,
    _AUTO_POSTER_PROMPT,
    _AUTO_POSTER_QUEUE_CONFIG,
    _AUTO_VIDEO_COUNT,
    _AUTO_WEBSITE_PROMPT,
    _DEFAULT_BUILDER_APP_MARKER,
    logger,
)
from app.modules.packs.onboarding.api import (
    dispatch_onboarding_job_from_api as _dispatch_onboarding_job_from_api_impl,
    enqueue_onboarding_job as _enqueue_onboarding_job_impl,
    get_onboarding_job_status as _get_onboarding_job_status_impl,
    request_onboarding_job_pause as _request_onboarding_job_pause_impl,
    resume_onboarding_job as _resume_onboarding_job_impl,
)
from app.modules.packs.onboarding.bootstrap import _run_post_onboarding_bootstrap
from app.modules.packs.onboarding.brand_os_helpers import (
    _get_existing_onboarding_brand_os,
    _sync_pack_core_concept,
)
from app.modules.packs.onboarding.fingerprints import (
    _build_onboarding_context,
    _compute_brand_identity_input_fingerprint,
    _compute_brand_os_input_fingerprint,
    _compute_logo_input_fingerprint,
    _compute_normalize_input_fingerprint,
    _compute_poster_flyers_input_fingerprint,
    _compute_qa_review_input_fingerprint,
    _compute_starter_brand_input_fingerprint,
    _compute_video_briefs_input_fingerprint,
    _compute_video_render_input_fingerprint,
    _compute_website_input_fingerprint,
    _extract_palette,
    _has_final_logo_output,
    _has_starter_brand_outputs,
    _resolve_brand_name,
    _resolve_vibe_chips,
    compute_onboarding_input_fingerprint,
    onboarding_job_matches_current_inputs,
)
from app.modules.packs.onboarding.generated_assets import (
    _build_auto_generation_messages,
    _collect_stream_text,
    _count_existing_auto_posters,
    _default_builder_files,
    _expected_auto_poster_names,
    _extract_poster_template_id,
    _has_generated_website_project,
    _parse_generated_files,
    _parse_generation_summary,
)
from app.modules.packs.onboarding.lineage import build_artifact_lineage
from app.modules.packs.onboarding.job_store import (
    load_pack_and_job as _load_pack_and_job_impl,
    log_job_event as _log_job_event_impl,
    mark_stage as _mark_stage_impl,
    persist_job as _persist_job_impl,
    raise_if_pause_requested as _raise_if_pause_requested_impl,
)
from app.modules.packs.onboarding.repair import (
    build_repair_plan,
    build_repair_plan_from_qa,
    recommend_repair_from_qa,
)
from app.modules.packs.onboarding.runtime import (
    build_onboarding_job_api_runtime,
    build_onboarding_job_control_runtime,
    build_onboarding_job_runner_runtime,
    build_onboarding_job_store_runtime,
    build_onboarding_pipeline_runtime,
)
from app.modules.packs.onboarding.runner import (
    run_onboarding_job as _run_onboarding_job_impl,
    run_onboarding_pipeline as _run_onboarding_pipeline_impl,
)
from app.modules.packs.onboarding.stages.brand_identity import (
    BrandIdentityStageRuntime,
    run_brand_identity_stage as _run_brand_identity_stage_impl,
)
from app.modules.packs.onboarding.stages.brand_os import (
    BrandOSStageRuntime,
    run_brand_os_stage as _run_brand_os_stage_impl,
)
from app.modules.packs.onboarding.stages.logo import (
    LogoStageRuntime,
    run_logo_stage as _run_logo_stage_impl,
)
from app.modules.packs.onboarding.stages.normalize_input import (
    NormalizeInputStageRuntime,
    run_normalize_input_stage as _run_normalize_input_stage_impl,
)
from app.modules.packs.onboarding.stages.poster_flyers import (
    PosterFlyersStageRuntime,
    run_poster_flyers_stage as _run_poster_flyers_stage_impl,
)
from app.modules.packs.onboarding.stages.qa_review import (
    QAReviewStageRuntime,
    run_qa_review_stage as _run_qa_review_stage_impl,
)
from app.modules.packs.onboarding.stages.starter_brand import (
    StarterBrandStageRuntime,
    run_starter_brand_stage as _run_starter_brand_stage_impl,
)
from app.modules.packs.onboarding.stages.videos import (
    VideoBriefsStageRuntime,
    VideoRenderStageRuntime,
    run_video_briefs_stage as _run_video_briefs_stage_impl,
    run_video_render_stage as _run_video_render_stage_impl,
)
from app.modules.packs.onboarding.stages.website import (
    WebsiteStageRuntime,
    run_website_stage as _run_website_stage_impl,
)
from app.modules.packs.onboarding.state import (
    _append_job_event,
    _build_public_job_stages,
    _default_job_events,
    _default_job_stages,
    _get_cached_fingerprint,
    _get_job_data,
    _map_internal_stage_to_public,
    _pause_job,
    _public_stage_summary,
    _set_job_data,
    _set_stage_state,
)
from app.modules.packs.onboarding_queue import dispatch_onboarding_job, redis_queue_enabled
from app.modules.packs.services import (
    append_suggested_logos,
    merge_onboarding_answers,
    resolve_pack_target_audience,
)


def _job_api_runtime():
    return build_onboarding_job_api_runtime(
        get_job_data=_get_job_data,
        set_job_data=_set_job_data,
        append_job_event=_append_job_event,
        default_job_stages=_default_job_stages,
        default_job_events=_default_job_events,
        iso_now=_iso_now,
        compute_onboarding_input_fingerprint=compute_onboarding_input_fingerprint,
        build_public_job_stages=_build_public_job_stages,
        public_stage_summary=_public_stage_summary,
        map_internal_stage_to_public=_map_internal_stage_to_public,
        pause_job=_pause_job,
        onboarding_job_max_attempts=ONBOARDING_JOB_MAX_ATTEMPTS,
        active_statuses=ACTIVE_ONBOARDING_JOB_STATUSES,
        redis_queue_enabled=redis_queue_enabled,
        dispatch_onboarding_job=dispatch_onboarding_job,
    )


def _job_store_runtime():
    return build_onboarding_job_store_runtime(
        pack_model=Pack,
        get_job_data=_get_job_data,
        set_job_data=_set_job_data,
    )


def _job_control_runtime():
    return build_onboarding_job_control_runtime(
        load_pack_and_job=_load_pack_and_job,
        persist_job=_persist_job,
        append_job_event=_append_job_event,
        set_stage_state=_set_stage_state,
        pause_requested_exception=OnboardingPauseRequested,
    )


def _pipeline_runtime():
    return build_onboarding_pipeline_runtime(
        load_pack_and_job=_load_pack_and_job,
        raise_if_pause_requested=_raise_if_pause_requested,
        run_normalize_input_stage=_run_normalize_input_stage,
        run_brand_os_stage=_run_brand_os_stage,
        run_brand_identity_stage=_run_brand_identity_stage,
        run_website_stage=_run_website_stage,
        run_poster_flyers_stage=_run_poster_flyers_stage,
        run_video_briefs_stage=_run_video_briefs_stage,
        run_video_render_stage=_run_video_render_stage,
        run_qa_review_stage=_run_qa_review_stage,
        mark_stage=_mark_stage,
        run_post_onboarding_bootstrap=_run_post_onboarding_bootstrap,
        utc_now=utc_now,
        stage_normalize_input=STAGE_NORMALIZE_INPUT,
        stage_brand_os=STAGE_BRAND_OS,
        stage_brand_identity=STAGE_BRAND_IDENTITY,
        stage_website=STAGE_WEBSITE,
        stage_poster_flyers=STAGE_POSTER_FLYERS,
        stage_video_briefs=STAGE_VIDEO_BRIEFS,
        stage_video_render=STAGE_VIDEO_RENDER,
        stage_qa_review=STAGE_QA_REVIEW,
        stage_order=ONBOARDING_JOB_STAGES,
    )


def _job_runner_runtime():
    return build_onboarding_job_runner_runtime(
        session_factory=SessionLocal,
        reset_db_query_stats=reset_db_query_stats,
        load_pack_and_job=_load_pack_and_job,
        append_job_event=_append_job_event,
        set_job_data=_set_job_data,
        iso_now=_iso_now,
        pause_job=_pause_job,
        run_onboarding_pipeline=_run_onboarding_pipeline,
        logger=logger,
        get_db_query_count=get_db_query_count,
        get_db_query_duration_ms=get_db_query_duration_ms,
        onboarding_pause_requested_exception=OnboardingPauseRequested,
        onboarding_job_max_attempts=ONBOARDING_JOB_MAX_ATTEMPTS,
        prepare_retry_job=_prepare_retry_job,
    )


def _log_job_event(
    db: Session,
    pack_id: UUID,
    job_id: str,
    message: str,
    *,
    stage_name: str | None = None,
    level: str = "info",
) -> Pack:
    runtime = _job_control_runtime()
    return _log_job_event_impl(
        db,
        pack_id,
        job_id,
        message,
        runtime,
        stage_name=stage_name,
        level=level,
    )


def _load_pack_and_job(
    db: Session,
    pack_id: UUID,
    job_id: str,
) -> tuple[Pack | None, dict[str, Any] | None]:
    runtime = _job_store_runtime()
    return _load_pack_and_job_impl(db, pack_id, job_id, runtime)


def _persist_job(db: Session, pack: Pack, job: dict[str, Any]) -> Pack:
    runtime = _job_store_runtime()
    return _persist_job_impl(db, pack, job, runtime)


def _raise_if_pause_requested(db: Session, pack_id: UUID, job_id: str) -> None:
    runtime = _job_control_runtime()
    return _raise_if_pause_requested_impl(db, pack_id, job_id, runtime)


def _mark_stage(
    db: Session,
    pack_id: UUID,
    job_id: str,
    stage_name: str,
    status: str,
    *,
    error: str | None = None,
    data: dict[str, Any] | None = None,
) -> Pack:
    runtime = _job_control_runtime()
    return _mark_stage_impl(
        db,
        pack_id,
        job_id,
        stage_name,
        status,
        runtime,
        error=error,
        data=data,
    )


def _run_normalize_input_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = NormalizeInputStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        get_artifact=_get_artifact,
        get_artifact_envelope=_get_artifact_envelope,
        save_artifact=_save_artifact,
        compute_input_fingerprint=_compute_normalize_input_fingerprint,
        resolve_brand_name=_resolve_brand_name,
        resolve_target_audience=resolve_pack_target_audience,
        resolve_vibe_chips=_resolve_vibe_chips,
        text_or_none=_text_or_none,
        iso_now=_iso_now,
        stage_name=STAGE_NORMALIZE_INPUT,
        input_fingerprint_key=NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY,
        artifact_type=ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
    )
    return _run_normalize_input_stage_impl(
        db=db,
        pack_id=pack_id,
        job_id=job_id,
        runtime=runtime,
    )


def _run_starter_brand_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = StarterBrandStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        append_suggested_logos=append_suggested_logos,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_starter_brand_input_fingerprint,
        has_starter_brand_outputs=_has_starter_brand_outputs,
        get_cached_fingerprint=_get_cached_fingerprint,
        resolve_brand_name=_resolve_brand_name,
        resolve_vibe_chips=_resolve_vibe_chips,
        build_onboarding_context=_build_onboarding_context,
        iso_now=_iso_now,
        stage_name=STAGE_STARTER_BRAND,
        input_fingerprint_key=STARTER_BRAND_INPUT_FINGERPRINT_KEY,
        normalized_artifact_type=ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
        brand_os_artifact_type=ARTIFACT_TYPE_BRAND_OS,
        artifact_type=ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    )
    return _run_starter_brand_stage_impl(
        db=db,
        pack_id=pack_id,
        job_id=job_id,
        runtime=runtime,
    )


def _run_brand_identity_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = BrandIdentityStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        get_existing_onboarding_brand_os=_get_existing_onboarding_brand_os,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        append_suggested_logos=append_suggested_logos,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_brand_identity_input_fingerprint,
        get_cached_fingerprint=_get_cached_fingerprint,
        resolve_brand_name=_resolve_brand_name,
        resolve_vibe_chips=_resolve_vibe_chips,
        build_onboarding_context=_build_onboarding_context,
        extract_palette=_extract_palette,
        summary_text_or_none=_summary_text_or_none,
        iso_now=_iso_now,
        stage_name=STAGE_BRAND_IDENTITY,
        input_fingerprint_key=BRAND_IDENTITY_INPUT_FINGERPRINT_KEY,
        normalized_artifact_type=ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
        brand_os_artifact_type=ARTIFACT_TYPE_BRAND_OS,
        artifact_type=ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    )
    return _run_brand_identity_stage_impl(
        db=db,
        pack_id=pack_id,
        job_id=job_id,
        runtime=runtime,
    )


def _run_brand_os_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = BrandOSStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        get_existing_onboarding_brand_os=_get_existing_onboarding_brand_os,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        sync_pack_core_concept=_sync_pack_core_concept,
        compute_input_fingerprint=_compute_brand_os_input_fingerprint,
        iso_now=_iso_now,
        stage_name=STAGE_BRAND_OS,
        input_fingerprint_key=BRAND_OS_INPUT_FINGERPRINT_KEY,
        normalized_artifact_type=ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
        artifact_type=ARTIFACT_TYPE_BRAND_OS,
    )
    return _run_brand_os_stage_impl(db=db, pack_id=pack_id, job_id=job_id, runtime=runtime)


def _run_logo_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = LogoStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        get_existing_onboarding_brand_os=_get_existing_onboarding_brand_os,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        append_suggested_logos=append_suggested_logos,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_logo_input_fingerprint,
        has_final_logo_output=_has_final_logo_output,
        get_cached_fingerprint=_get_cached_fingerprint,
        extract_palette=_extract_palette,
        summary_text_or_none=_summary_text_or_none,
        iso_now=_iso_now,
        stage_name=STAGE_LOGO,
        input_fingerprint_key=LOGO_INPUT_FINGERPRINT_KEY,
        normalized_artifact_type=ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
        brand_os_artifact_type=ARTIFACT_TYPE_BRAND_OS,
        artifact_type=ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    )
    return _run_logo_stage_impl(db=db, pack_id=pack_id, job_id=job_id, runtime=runtime)


def _run_website_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = WebsiteStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_website_input_fingerprint,
        get_cached_fingerprint=_get_cached_fingerprint,
        has_generated_website_project=_has_generated_website_project,
        default_builder_files=_default_builder_files,
        collect_stream_text=_collect_stream_text,
        parse_generated_files=_parse_generated_files,
        parse_generation_summary=_parse_generation_summary,
        text_or_none=_text_or_none,
        iso_now=_iso_now,
        stage_name=STAGE_WEBSITE,
        input_fingerprint_key=WEBSITE_INPUT_FINGERPRINT_KEY,
        auto_website_prompt=_AUTO_WEBSITE_PROMPT,
        default_builder_app_marker=_DEFAULT_BUILDER_APP_MARKER,
        artifact_type=ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
    )
    return _run_website_stage_impl(db=db, pack_id=pack_id, job_id=job_id, runtime=runtime)


def _run_poster_flyers_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = PosterFlyersStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        raise_if_pause_requested=_raise_if_pause_requested,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_poster_flyers_input_fingerprint,
        expected_auto_poster_names=_expected_auto_poster_names,
        count_existing_auto_posters=_count_existing_auto_posters,
        get_cached_fingerprint=_get_cached_fingerprint,
        iso_now=_iso_now,
        auto_poster_queue_config=_AUTO_POSTER_QUEUE_CONFIG,
        auto_poster_prompt=_AUTO_POSTER_PROMPT,
        collect_stream_text=_collect_stream_text,
        parse_generated_files=_parse_generated_files,
        extract_poster_template_id=_extract_poster_template_id,
        build_auto_generation_messages=_build_auto_generation_messages,
        stage_name=STAGE_POSTER_FLYERS,
        input_fingerprint_key=POSTER_FLYERS_INPUT_FINGERPRINT_KEY,
        website_artifact_type=ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
        artifact_type=ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
    )
    return _run_poster_flyers_stage_impl(
        db=db,
        pack_id=pack_id,
        job_id=job_id,
        runtime=runtime,
    )


def _run_video_briefs_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = VideoBriefsStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_video_briefs_input_fingerprint,
        get_cached_fingerprint=_get_cached_fingerprint,
        iso_now=_iso_now,
        auto_video_count=_AUTO_VIDEO_COUNT,
        stage_name=STAGE_VIDEO_BRIEFS,
        input_fingerprint_key=VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY,
        website_artifact_type=ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
        creative_artifact_type=ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
        artifact_type=ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
    )
    return _run_video_briefs_stage_impl(db=db, pack_id=pack_id, job_id=job_id, runtime=runtime)


def _run_video_render_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = VideoRenderStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        get_artifact=_get_artifact,
        save_artifact=_save_artifact,
        merge_onboarding_answers=merge_onboarding_answers,
        compute_input_fingerprint=_compute_video_render_input_fingerprint,
        get_cached_fingerprint=_get_cached_fingerprint,
        iso_now=_iso_now,
        auto_video_count=_AUTO_VIDEO_COUNT,
        stage_name=STAGE_VIDEO_RENDER,
        input_fingerprint_key=VIDEO_RENDER_INPUT_FINGERPRINT_KEY,
        brief_artifact_type=ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
        artifact_type=ARTIFACT_TYPE_VIDEO_RENDER_RESULT,
    )
    return _run_video_render_stage_impl(db=db, pack_id=pack_id, job_id=job_id, runtime=runtime)


def _run_qa_review_stage(db: Session, pack_id: UUID, job_id: str) -> Pack:
    runtime = QAReviewStageRuntime(
        load_pack_and_job=_load_pack_and_job,
        mark_stage=_mark_stage,
        log_job_event=_log_job_event,
        get_artifact=_get_artifact,
        get_artifact_envelope=_get_artifact_envelope,
        get_artifact_versions=_get_artifact_versions,
        save_artifact=_save_artifact,
        compute_input_fingerprint=_compute_qa_review_input_fingerprint,
        iso_now=_iso_now,
        expected_auto_poster_names=_expected_auto_poster_names,
        auto_video_count=_AUTO_VIDEO_COUNT,
        default_builder_app_marker=_DEFAULT_BUILDER_APP_MARKER,
        stage_name=STAGE_QA_REVIEW,
        input_fingerprint_key=QA_REVIEW_INPUT_FINGERPRINT_KEY,
        artifact_type=ARTIFACT_TYPE_QA_REPORT,
        normalized_artifact_type=ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
        brand_os_artifact_type=ARTIFACT_TYPE_BRAND_OS,
    )
    return _run_qa_review_stage_impl(
        db=db,
        pack_id=pack_id,
        job_id=job_id,
        runtime=runtime,
    )


def _run_onboarding_pipeline(db: Session, pack_id: UUID, job_id: str) -> None:
    runtime = _pipeline_runtime()
    return _run_onboarding_pipeline_impl(db=db, pack_id=pack_id, job_id=job_id, runtime=runtime)


def _repair_job_stage_states(selected_stages: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    states = _default_job_stages()
    selected = set(selected_stages)
    for stage_name, stage_state in states.items():
        if stage_name not in selected:
            stage_state["status"] = "skipped"
            stage_state["completed_at"] = _iso_now()
    return states


def _prepare_retry_job(
    db: Session,
    pack: Pack,
    job: dict[str, Any],
    failed_stage: str | None,
    exc: Exception,
) -> str | None:
    del db
    if failed_stage != STAGE_QA_REVIEW:
        return None
    report = _get_artifact(pack, ARTIFACT_TYPE_QA_REPORT)
    if not report:
        return None
    recommendation = recommend_repair_from_qa(report)
    if not recommendation.stage_name or not recommendation.auto_repairable:
        return None
    plan = build_repair_plan_from_qa(report, include_downstream=True)
    job["mode"] = "qa_repair"
    job["requested_stage"] = plan.requested_stage
    job["selected_stages"] = list(plan.selected_stages)
    job["repair_reason"] = recommendation.reason or _text_or_none(str(exc), limit=500)
    job["stages"] = _repair_job_stage_states(plan.selected_stages)
    pack.onboarding_background_completed_at = None
    return f"Retrying onboarding automation with targeted QA repair from {plan.requested_stage}."


def _queue_stage_repair_job(
    pack: Pack,
    *,
    requested_stage: str,
    selected_stages: tuple[str, ...],
    mode: str = "stage_repair",
    reason: str | None = None,
) -> dict[str, Any]:
    runtime = _job_api_runtime()
    existing_job = runtime.get_job_data(pack)
    if existing_job and str(existing_job.get("status") or "").strip() in ACTIVE_ONBOARDING_JOB_STATUSES:
        raise ValueError("An onboarding job is already running for this project.")

    job = {
        "job_id": str(uuid.uuid4()),
        "status": "queued",
        "mode": mode,
        "requested_stage": requested_stage,
        "selected_stages": list(selected_stages),
        "repair_reason": _text_or_none(reason, limit=500),
        "input_fingerprint": runtime.compute_onboarding_input_fingerprint(pack),
        "attempt": 0,
        "max_attempts": runtime.onboarding_job_max_attempts,
        "queued_at": runtime.iso_now(),
        "started_at": None,
        "completed_at": None,
        "last_error": None,
        "pause_requested": False,
        "paused_at": None,
        "current_stage": None,
        "stages": _repair_job_stage_states(selected_stages),
        "events": runtime.default_job_events(),
    }
    message = f"Queued onboarding repair from {requested_stage}."
    if reason:
        message = f"{message} Reason: {_text_or_none(reason, limit=200)}"
    runtime.append_job_event(job, message, level="info")
    runtime.set_job_data(pack, job)
    pack.onboarding_background_completed_at = None
    return job


def enqueue_onboarding_job(db: Session, pack_id: UUID) -> dict[str, Any]:
    pack = db.get(Pack, pack_id)
    if not pack:
        raise DomainNotFoundError("Pack not found")
    runtime = _job_api_runtime()
    job = _enqueue_onboarding_job_impl(pack, runtime)
    job["mode"] = "full_run"
    job["requested_stage"] = None
    job["selected_stages"] = list(ONBOARDING_JOB_STAGES)
    runtime.set_job_data(pack, job)
    db.flush()
    return job


def enqueue_onboarding_stage_repair(
    db: Session,
    pack_id: UUID,
    *,
    stage_name: str,
    include_downstream: bool = True,
    reason: str | None = None,
) -> dict[str, Any]:
    pack = db.get(Pack, pack_id)
    if not pack:
        raise DomainNotFoundError("Pack not found")
    plan = build_repair_plan(stage_name, include_downstream=include_downstream)
    job = _queue_stage_repair_job(
        pack,
        requested_stage=plan.requested_stage,
        selected_stages=plan.selected_stages,
        reason=reason,
    )
    db.flush()
    return job


def enqueue_onboarding_qa_repair(
    db: Session,
    pack_id: UUID,
    *,
    include_downstream: bool = True,
    reason: str | None = None,
) -> dict[str, Any]:
    pack = db.get(Pack, pack_id)
    if not pack:
        raise DomainNotFoundError("Pack not found")
    report = _get_artifact(pack, ARTIFACT_TYPE_QA_REPORT)
    if not report:
        raise ValueError("No QA report is available for this project yet.")
    recommendation = recommend_repair_from_qa(report)
    if not recommendation.stage_name:
        raise ValueError("The latest QA report does not include a repairable stage recommendation.")
    plan = build_repair_plan_from_qa(report, include_downstream=include_downstream)
    job = _queue_stage_repair_job(
        pack,
        requested_stage=plan.requested_stage,
        selected_stages=plan.selected_stages,
        mode="qa_repair",
        reason=reason or recommendation.reason,
    )
    db.flush()
    return job


def get_onboarding_artifact_lineage(pack: Pack) -> list[dict[str, Any]]:
    return build_artifact_lineage(pack)


def get_onboarding_job_status(pack: Pack) -> dict[str, Any]:
    runtime = _job_api_runtime()
    payload = _get_onboarding_job_status_impl(pack, runtime)
    job = runtime.get_job_data(pack) or {}
    selected_stages = job.get("selected_stages")
    normalized_selected_stages: list[str] | None = None
    if isinstance(selected_stages, list) and selected_stages:
        normalized_selected_stages = []
        for stage_name in selected_stages:
            normalized_stage_name = str(stage_name or "").strip()
            if normalized_stage_name in {STAGE_STARTER_BRAND, STAGE_LOGO}:
                normalized_stage_name = STAGE_BRAND_IDENTITY
            if normalized_stage_name and normalized_stage_name not in normalized_selected_stages:
                normalized_selected_stages.append(normalized_stage_name)
    payload["mode"] = job.get("mode") or "full_run"
    requested_stage = str(job.get("requested_stage") or "").strip() or None
    if requested_stage in {STAGE_STARTER_BRAND, STAGE_LOGO}:
        requested_stage = STAGE_BRAND_IDENTITY
    payload["requested_stage"] = requested_stage
    payload["selected_stages"] = (
        normalized_selected_stages
        if normalized_selected_stages
        else (list(ONBOARDING_JOB_STAGES) if job else None)
    )
    payload["repair_reason"] = job.get("repair_reason")
    payload["artifacts"] = get_onboarding_artifact_lineage(pack)
    qa_report = _get_artifact(pack, ARTIFACT_TYPE_QA_REPORT)
    qa_recommendation = recommend_repair_from_qa(qa_report) if qa_report else None
    payload["qa_overall_status"] = getattr(qa_report, "overall_status", None)
    payload["qa_consistency_score"] = getattr(qa_report, "consistency_score", None)
    payload["qa_recommended_repair_stage"] = (
        getattr(qa_report, "recommended_repair_stage", None)
        or (qa_recommendation.stage_name if qa_recommendation else None)
    )
    payload["qa_recommended_repair_reason"] = (
        getattr(qa_report, "recommended_repair_reason", None)
        or (qa_recommendation.reason if qa_recommendation else None)
    )
    payload["qa_auto_repairable"] = bool(
        getattr(qa_report, "auto_repairable", False)
        or (qa_recommendation.auto_repairable if qa_recommendation else False)
    )
    return payload


def dispatch_onboarding_job_from_api(
    pack_id: UUID,
    job_id: str,
    *,
    delay_seconds: int = 0,
    force: bool = False,
) -> bool:
    runtime = _job_api_runtime()
    return _dispatch_onboarding_job_from_api_impl(
        pack_id=pack_id,
        job_id=job_id,
        runtime=runtime,
        delay_seconds=delay_seconds,
        force=force,
    )


def request_onboarding_job_pause(db: Session, pack_id: UUID) -> dict[str, Any]:
    pack = db.get(Pack, pack_id)
    if not pack:
        raise DomainNotFoundError("Pack not found")
    runtime = _job_api_runtime()
    return _request_onboarding_job_pause_impl(db, pack, runtime)


def resume_onboarding_job(db: Session, pack_id: UUID) -> dict[str, Any]:
    pack = db.get(Pack, pack_id)
    if not pack:
        raise DomainNotFoundError("Pack not found")
    runtime = _job_api_runtime()
    return _resume_onboarding_job_impl(db, pack, runtime)


def run_onboarding_job(pack_id: UUID, job_id: str) -> OnboardingRunResult:
    runtime = _job_runner_runtime()
    return _run_onboarding_job_impl(pack_id=pack_id, job_id=job_id, runtime=runtime)
