"""Onboarding worker pipeline and run-loop helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.common import OnboardingRunResult


@dataclass(frozen=True)
class OnboardingPipelineRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    raise_if_pause_requested: Callable[[Session, UUID, str], None]
    run_normalize_input_stage: Callable[[Session, UUID, str], Any]
    run_brand_os_stage: Callable[[Session, UUID, str], Any]
    run_brand_identity_stage: Callable[[Session, UUID, str], Any]
    run_website_stage: Callable[[Session, UUID, str], Any]
    run_poster_flyers_stage: Callable[[Session, UUID, str], Any]
    run_video_briefs_stage: Callable[[Session, UUID, str], Any]
    run_video_render_stage: Callable[[Session, UUID, str], Any]
    run_qa_review_stage: Callable[[Session, UUID, str], Any]
    mark_stage: Callable[..., Any]
    run_post_onboarding_bootstrap: Callable[[Session, Any], Any]
    utc_now: Callable[[], Any]
    stage_normalize_input: str
    stage_brand_os: str
    stage_brand_identity: str
    stage_website: str
    stage_poster_flyers: str
    stage_video_briefs: str
    stage_video_render: str
    stage_qa_review: str
    stage_order: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingJobRunnerRuntime:
    session_factory: Callable[[], Session]
    reset_db_query_stats: Callable[[], None]
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    append_job_event: Callable[..., None]
    set_job_data: Callable[[Any, dict[str, Any]], None]
    iso_now: Callable[[], str]
    pause_job: Callable[..., None]
    run_onboarding_pipeline: Callable[[Session, UUID, str], None]
    logger: Any
    get_db_query_count: Callable[[], int]
    get_db_query_duration_ms: Callable[[], float]
    onboarding_pause_requested_exception: type[BaseException]
    onboarding_job_max_attempts: int
    prepare_retry_job: Callable[[Session, Any, dict[str, Any], str | None, Exception], str | None] | None = None


def run_onboarding_pipeline(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: OnboardingPipelineRuntime,
) -> None:
    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        return

    answers = pack.onboarding_answers or {}
    is_existing_brand = answers.get("has_existing_brand") == "yes"
    requested_stage = str(job.get("requested_stage") or "").strip()
    raw_selected_stage_names = job.get("selected_stages") if isinstance(job.get("selected_stages"), list) else None
    selected_stage_names = None
    if raw_selected_stage_names:
        normalized_selected_stages: list[str] = []
        for stage_name in raw_selected_stage_names:
            normalized_stage_name = str(stage_name or "").strip()
            if normalized_stage_name in {"starter_brand", "logo"}:
                normalized_stage_name = runtime.stage_brand_identity
            if normalized_stage_name and normalized_stage_name not in normalized_selected_stages:
                normalized_selected_stages.append(normalized_stage_name)
        selected_stage_names = normalized_selected_stages or None
    selected_stages = tuple(
        stage_name
        for stage_name in runtime.stage_order
        if not selected_stage_names or stage_name in selected_stage_names
    ) or runtime.stage_order
    selected_stage_set = set(selected_stages)
    force_brand_identity = requested_stage in {"brand_identity", runtime.stage_brand_identity, "starter_brand", "logo"}

    if runtime.stage_normalize_input in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_normalize_input_stage(db, pack_id, job_id)

    if runtime.stage_brand_os in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_brand_os_stage(db, pack_id, job_id)

    if runtime.stage_brand_identity in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        if is_existing_brand and not force_brand_identity:
            runtime.mark_stage(db, pack_id, job_id, runtime.stage_brand_identity, "skipped")
        else:
            runtime.run_brand_identity_stage(db, pack_id, job_id)

    if runtime.stage_website in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_website_stage(db, pack_id, job_id)
    if runtime.stage_poster_flyers in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_poster_flyers_stage(db, pack_id, job_id)
    if runtime.stage_video_briefs in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_video_briefs_stage(db, pack_id, job_id)
    if runtime.stage_video_render in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_video_render_stage(db, pack_id, job_id)
    if runtime.stage_qa_review in selected_stage_set:
        runtime.raise_if_pause_requested(db, pack_id, job_id)
        runtime.run_qa_review_stage(db, pack_id, job_id)

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        return
    pack.onboarding_background_completed_at = runtime.utc_now()
    db.commit()
    db.refresh(pack)
    if str(job.get("mode") or "full_run") == "full_run":
        runtime.run_post_onboarding_bootstrap(db, pack)


def run_onboarding_job(
    *,
    pack_id: UUID,
    job_id: str,
    runtime: OnboardingJobRunnerRuntime,
) -> OnboardingRunResult:
    db = runtime.session_factory()
    runtime.reset_db_query_stats()
    try:
        pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
        if not pack or not job:
            return OnboardingRunResult(retry=False, attempt=0, clear_dispatch=True)
        if job["status"] in {"completed", "paused"}:
            return OnboardingRunResult(
                retry=False,
                attempt=int(job.get("attempt") or 0),
                clear_dispatch=True,
            )

        attempt = int(job.get("attempt") or 0) + 1
        job["attempt"] = attempt
        job["status"] = "running"
        job["started_at"] = job.get("started_at") or runtime.iso_now()
        job["last_error"] = None
        job["paused_at"] = None
        runtime.append_job_event(job, f"Worker picked up onboarding job (attempt {attempt}).")
        runtime.set_job_data(pack, job)
        db.commit()

        try:
            runtime.run_onboarding_pipeline(db, pack_id, job_id)
        except runtime.onboarding_pause_requested_exception:
            try:
                db.rollback()
            except Exception:
                pass
            pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
            if not pack or not job:
                return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
            runtime.pause_job(job, message="Paused onboarding automation.")
            runtime.set_job_data(pack, job)
            db.commit()
            return OnboardingRunResult(
                retry=False,
                attempt=attempt,
                clear_dispatch=True,
            )
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
            if not pack or not job:
                return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
            should_retry = attempt < int(job.get("max_attempts") or runtime.onboarding_job_max_attempts)
            failed_stage = job.get("current_stage") or next(
                (
                    stage_name
                    for stage_name, stage_state in reversed(list((job.get("stages") or {}).items()))
                    if isinstance(stage_state, dict) and str(stage_state.get("status") or "") == "failed"
                ),
                None,
            )
            retry_message = "Retrying onboarding automation in the background."
            if should_retry and runtime.prepare_retry_job is not None:
                prepared_message = runtime.prepare_retry_job(db, pack, job, failed_stage, exc)
                if prepared_message:
                    retry_message = prepared_message
            job["status"] = "queued" if should_retry else "failed"
            job["last_error"] = str(exc)[:2000]
            job["pause_requested"] = False
            job["paused_at"] = None
            job["current_stage"] = None
            runtime.append_job_event(
                job,
                f"Attempt {attempt} failed: {job['last_error']}",
                stage_name=failed_stage,
                level="error",
            )
            if should_retry:
                runtime.append_job_event(
                    job,
                    retry_message,
                    stage_name=failed_stage,
                )
            runtime.set_job_data(pack, job)
            db.commit()
            return OnboardingRunResult(
                retry=should_retry,
                attempt=attempt,
                clear_dispatch=not should_retry,
            )

        pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
        if not pack or not job:
            return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
        job["status"] = "completed"
        job["completed_at"] = runtime.iso_now()
        job["last_error"] = None
        job["pause_requested"] = False
        job["paused_at"] = None
        job["current_stage"] = None
        runtime.append_job_event(job, "Onboarding automation finished successfully.")
        runtime.set_job_data(pack, job)
        db.commit()
        return OnboardingRunResult(retry=False, attempt=attempt, clear_dispatch=True)
    finally:
        runtime.logger.info(
            "onboarding_job_db_usage | pack_id=%s | job_id=%s | queries=%s | query_time_ms=%.2f",
            pack_id,
            job_id,
            runtime.get_db_query_count(),
            runtime.get_db_query_duration_ms(),
        )
        db.close()
