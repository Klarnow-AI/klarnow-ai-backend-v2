"""Runtime factory helpers for onboarding orchestration modules."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.api import OnboardingJobApiRuntime
from app.modules.packs.onboarding.job_store import (
    OnboardingJobControlRuntime,
    OnboardingJobStoreRuntime,
)
from app.modules.packs.onboarding.runner import (
    OnboardingJobRunnerRuntime,
    OnboardingPipelineRuntime,
)


def build_onboarding_job_api_runtime(
    *,
    get_job_data: Callable[[Any], dict[str, Any] | None],
    set_job_data: Callable[[Any, dict[str, Any]], None],
    append_job_event: Callable[..., None],
    default_job_stages: Callable[[], dict[str, Any]],
    default_job_events: Callable[[], list[dict[str, Any]]],
    iso_now: Callable[[], str],
    compute_onboarding_input_fingerprint: Callable[[Any], str],
    build_public_job_stages: Callable[[dict[str, Any]], dict[str, dict[str, Any]]],
    public_stage_summary: Callable[[dict[str, Any]], dict[str, Any]],
    map_internal_stage_to_public: Callable[[str | None], str | None],
    pause_job: Callable[..., None],
    onboarding_job_max_attempts: int,
    active_statuses: Collection[str],
    redis_queue_enabled: Callable[[], bool],
    dispatch_onboarding_job: Callable[..., bool],
) -> OnboardingJobApiRuntime:
    return OnboardingJobApiRuntime(
        get_job_data=get_job_data,
        set_job_data=set_job_data,
        append_job_event=append_job_event,
        default_job_stages=default_job_stages,
        default_job_events=default_job_events,
        iso_now=iso_now,
        compute_onboarding_input_fingerprint=compute_onboarding_input_fingerprint,
        build_public_job_stages=build_public_job_stages,
        public_stage_summary=public_stage_summary,
        map_internal_stage_to_public=map_internal_stage_to_public,
        pause_job=pause_job,
        onboarding_job_max_attempts=onboarding_job_max_attempts,
        active_statuses=active_statuses,
        redis_queue_enabled=redis_queue_enabled,
        dispatch_onboarding_job=dispatch_onboarding_job,
    )


def build_onboarding_job_store_runtime(
    *,
    pack_model: type[Any],
    get_job_data: Callable[[Any], dict[str, Any] | None],
    set_job_data: Callable[[Any, dict[str, Any]], None],
) -> OnboardingJobStoreRuntime:
    return OnboardingJobStoreRuntime(
        pack_model=pack_model,
        get_job_data=get_job_data,
        set_job_data=set_job_data,
    )


def build_onboarding_job_control_runtime(
    *,
    load_pack_and_job: Callable[[Session, Any, str], tuple[Any | None, dict[str, Any] | None]],
    persist_job: Callable[[Session, Any, dict[str, Any]], Any],
    append_job_event: Callable[..., None],
    set_stage_state: Callable[..., None],
    pause_requested_exception: type[BaseException],
) -> OnboardingJobControlRuntime:
    return OnboardingJobControlRuntime(
        load_pack_and_job=load_pack_and_job,
        persist_job=persist_job,
        append_job_event=append_job_event,
        set_stage_state=set_stage_state,
        pause_requested_exception=pause_requested_exception,
    )


def build_onboarding_pipeline_runtime(
    *,
    load_pack_and_job: Callable[[Session, Any, str], tuple[Any | None, dict[str, Any] | None]],
    raise_if_pause_requested: Callable[[Session, Any, str], None],
    run_normalize_input_stage: Callable[[Session, Any, str], Any],
    run_brand_os_stage: Callable[[Session, Any, str], Any],
    run_brand_identity_stage: Callable[[Session, Any, str], Any],
    run_website_stage: Callable[[Session, Any, str], Any],
    run_poster_flyers_stage: Callable[[Session, Any, str], Any],
    run_video_briefs_stage: Callable[[Session, Any, str], Any],
    run_video_render_stage: Callable[[Session, Any, str], Any],
    run_qa_review_stage: Callable[[Session, Any, str], Any],
    mark_stage: Callable[..., Any],
    run_post_onboarding_bootstrap: Callable[[Session, Any], Any],
    utc_now: Callable[[], Any],
    stage_normalize_input: str,
    stage_brand_os: str,
    stage_brand_identity: str,
    stage_website: str,
    stage_poster_flyers: str,
    stage_video_briefs: str,
    stage_video_render: str,
    stage_qa_review: str,
    stage_order: tuple[str, ...],
) -> OnboardingPipelineRuntime:
    return OnboardingPipelineRuntime(
        load_pack_and_job=load_pack_and_job,
        raise_if_pause_requested=raise_if_pause_requested,
        run_normalize_input_stage=run_normalize_input_stage,
        run_brand_os_stage=run_brand_os_stage,
        run_brand_identity_stage=run_brand_identity_stage,
        run_website_stage=run_website_stage,
        run_poster_flyers_stage=run_poster_flyers_stage,
        run_video_briefs_stage=run_video_briefs_stage,
        run_video_render_stage=run_video_render_stage,
        run_qa_review_stage=run_qa_review_stage,
        mark_stage=mark_stage,
        run_post_onboarding_bootstrap=run_post_onboarding_bootstrap,
        utc_now=utc_now,
        stage_normalize_input=stage_normalize_input,
        stage_brand_os=stage_brand_os,
        stage_brand_identity=stage_brand_identity,
        stage_website=stage_website,
        stage_poster_flyers=stage_poster_flyers,
        stage_video_briefs=stage_video_briefs,
        stage_video_render=stage_video_render,
        stage_qa_review=stage_qa_review,
        stage_order=stage_order,
    )


def build_onboarding_job_runner_runtime(
    *,
    session_factory: Callable[[], Session],
    reset_db_query_stats: Callable[[], None],
    load_pack_and_job: Callable[[Session, Any, str], tuple[Any | None, dict[str, Any] | None]],
    append_job_event: Callable[..., None],
    set_job_data: Callable[[Any, dict[str, Any]], None],
    iso_now: Callable[[], str],
    pause_job: Callable[..., None],
    run_onboarding_pipeline: Callable[[Session, Any, str], None],
    logger: Any,
    get_db_query_count: Callable[[], int],
    get_db_query_duration_ms: Callable[[], float],
    onboarding_pause_requested_exception: type[BaseException],
    onboarding_job_max_attempts: int,
    prepare_retry_job: Callable[[Session, Any, dict[str, Any], str | None, Exception], str | None] | None = None,
) -> OnboardingJobRunnerRuntime:
    return OnboardingJobRunnerRuntime(
        session_factory=session_factory,
        reset_db_query_stats=reset_db_query_stats,
        load_pack_and_job=load_pack_and_job,
        append_job_event=append_job_event,
        set_job_data=set_job_data,
        iso_now=iso_now,
        pause_job=pause_job,
        run_onboarding_pipeline=run_onboarding_pipeline,
        logger=logger,
        get_db_query_count=get_db_query_count,
        get_db_query_duration_ms=get_db_query_duration_ms,
        onboarding_pause_requested_exception=onboarding_pause_requested_exception,
        onboarding_job_max_attempts=onboarding_job_max_attempts,
        prepare_retry_job=prepare_retry_job,
    )
