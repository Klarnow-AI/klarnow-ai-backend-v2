"""Final QA onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import (
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_RENDER_RESULT,
    ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
    QAReport,
)
from app.modules.packs.onboarding.repair import recommend_repair_from_qa


@dataclass(frozen=True)
class QAReviewStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    get_artifact_envelope: Callable[[Any, str], Any | None]
    get_artifact_versions: Callable[[Any], dict[str, int]]
    save_artifact: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    iso_now: Callable[[], str]
    expected_auto_poster_names: Callable[[], list[str]]
    auto_video_count: int
    default_builder_app_marker: str
    stage_name: str
    input_fingerprint_key: str
    artifact_type: str
    normalized_artifact_type: str
    brand_os_artifact_type: str


def _contains_phrase(haystack: str, needle: str | None) -> bool:
    text = str(haystack or "").strip().lower()
    query = str(needle or "").strip().lower()
    return bool(text and query and query in text)


def _compact_text(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if str(part or "").strip())


def run_qa_review_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: QAReviewStageRuntime,
):
    from app.modules.brand_os.services import get_active_for_pack
    from app.modules.builder.services import get_for_pack_any
    from app.modules.creative.services import list_assets_for_pack

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    existing_envelope = runtime.get_artifact_envelope(pack, runtime.artifact_type)
    existing_report = runtime.get_artifact(pack, runtime.artifact_type)

    if stage["status"] == "completed" or (
        existing_envelope
        and str(existing_envelope.input_fingerprint or "") == input_fingerprint
        and getattr(existing_report, "overall_status", "passed") != "failed"
    ):
        pack.onboarding_answers = dict(pack.onboarding_answers or {})
        pack.onboarding_answers[runtime.input_fingerprint_key] = input_fingerprint
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={
                "artifact_type": runtime.artifact_type,
                "artifact_version": getattr(existing_envelope, "version", 0),
                "overall_status": getattr(existing_report, "overall_status", "passed"),
                "recommended_repair_stage": getattr(existing_report, "recommended_repair_stage", None),
            },
        )

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")

    normalized = runtime.get_artifact(pack, runtime.normalized_artifact_type)
    brand_os_artifact = runtime.get_artifact(pack, runtime.brand_os_artifact_type)
    brand_identity_artifact = runtime.get_artifact(pack, ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE)
    website_blueprint = runtime.get_artifact(pack, ARTIFACT_TYPE_WEBSITE_BLUEPRINT)
    creative_brief = runtime.get_artifact(pack, ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE)
    video_brief = runtime.get_artifact(pack, ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE)
    video_render_result = runtime.get_artifact(pack, ARTIFACT_TYPE_VIDEO_RENDER_RESULT)
    brand_os = get_active_for_pack(db, pack_id)
    project = get_for_pack_any(db, pack_id)
    assets = list_assets_for_pack(db, pack_id)
    expected_poster_names = set(runtime.expected_auto_poster_names())
    poster_assets = [asset for asset in assets if getattr(asset, "type", None) == "poster"]
    poster_names = {
        str(getattr(asset, "name", "")).strip()
        for asset in poster_assets
        if str(getattr(asset, "name", "")).strip()
    }
    video_assets = [asset for asset in assets if getattr(asset, "type", None) == "video"]

    passed_checks: list[str] = []
    warning_checks: list[str] = []
    failed_checks: list[str] = []
    repair_actions: list[str] = []

    if normalized:
        passed_checks.append("Normalized business profile is present.")
    else:
        failed_checks.append("Normalized business profile is missing.")
        repair_actions.append("Rerun the normalize_input stage before downstream generation.")

    if brand_os:
        passed_checks.append("Brand OS is present.")
    else:
        failed_checks.append("Brand OS is missing.")
        repair_actions.append("Rerun the brand_os stage to restore the strategic source of truth.")

    if brand_identity_artifact:
        passed_checks.append("Brand identity artifact is present.")
    else:
        warning_checks.append("Brand identity artifact is missing.")

    if website_blueprint:
        passed_checks.append("Website blueprint artifact is present.")
    else:
        warning_checks.append("Website blueprint artifact is missing.")

    if creative_brief:
        passed_checks.append("Creative brief artifact is present.")
    else:
        warning_checks.append("Creative brief artifact is missing.")

    if video_brief:
        passed_checks.append("Video brief artifact is present.")
    else:
        failed_checks.append("Video brief artifact is missing.")
        repair_actions.append("Rerun the video_briefs stage to restore the starter video scripts.")

    if video_render_result:
        passed_checks.append("Video render artifact is present.")
    elif len(video_assets) >= runtime.auto_video_count:
        warning_checks.append("Video render artifact is missing.")
        repair_actions.append("Rerun the video_render stage to persist the latest video render lineage.")

    app_code = ""
    if project and isinstance(getattr(project, "files", None), dict):
        app_code = str(project.files.get("/App.tsx") or project.files.get("App.tsx") or "").strip()
    if project and app_code and runtime.default_builder_app_marker not in app_code:
        passed_checks.append("Website project contains a usable App component.")
    else:
        failed_checks.append("Website output is missing or still on the placeholder app.")
        repair_actions.append("Rerun the website stage to regenerate the builder project.")

    missing_posters = sorted(expected_poster_names - poster_names)
    if not expected_poster_names or not missing_posters:
        passed_checks.append("Starter poster pack is present.")
    else:
        failed_checks.append(
            f"Starter poster pack is incomplete ({len(missing_posters)} file(s) missing)."
        )
        repair_actions.append("Rerun the poster_flyers stage to rebuild the starter poster set.")

    if len(video_assets) >= runtime.auto_video_count:
        passed_checks.append("Starter videos are present.")
    else:
        failed_checks.append(
            f"Starter video output is incomplete ({len(video_assets)}/{runtime.auto_video_count})."
        )
        repair_actions.append("Rerun the video_render stage to restore the starter video set.")

    combined_generated_text = _compact_text(
        [
            app_code,
            *[str(getattr(asset, "source_code", "") or "") for asset in assets],
            *[str(getattr(asset, "script", "") or "") for asset in assets],
        ]
    )
    primary_cta = getattr(normalized, "primary_cta", None) if normalized else None
    if primary_cta and _contains_phrase(combined_generated_text, primary_cta):
        passed_checks.append("Primary CTA appears in generated outputs.")
    elif primary_cta:
        warning_checks.append("Primary CTA does not clearly appear in the generated outputs.")
        repair_actions.append("Review website and creative copy to reinforce the primary CTA.")

    tone_preferences = list(getattr(normalized, "tone_preferences", []) or []) if normalized else []
    tone_attributes = list(getattr(brand_os_artifact, "tone_attributes", []) or []) if brand_os_artifact else []
    if tone_preferences and tone_attributes:
        normalized_tones = {item.lower() for item in tone_preferences}
        strategy_tones = {item.lower() for item in tone_attributes}
        if normalized_tones & strategy_tones:
            passed_checks.append("Tone cues are aligned between normalized input and Brand OS.")
        else:
            warning_checks.append("Tone cues differ between normalized input and Brand OS.")
            repair_actions.append("Review Brand OS voice traits against the normalized vibe chips.")
    elif tone_preferences or tone_attributes:
        warning_checks.append("Tone cues are only partially represented across the artifacts.")

    proof_points = list(getattr(normalized, "proof_points", []) or []) if normalized else []
    if proof_points and any(_contains_phrase(combined_generated_text, proof) for proof in proof_points):
        passed_checks.append("Proof points carry through into generated outputs.")
    elif proof_points:
        warning_checks.append("Proof points are not clearly visible in generated outputs.")
        repair_actions.append("Review website and creative outputs to surface stronger proof.")

    palette = (pack.onboarding_answers or {}).get("palette") if isinstance(pack.onboarding_answers, dict) else None
    if str((pack.onboarding_answers or {}).get("wordmark_svg_or_url") or "").strip() or isinstance(palette, dict):
        passed_checks.append("Visual identity signals are present.")
    else:
        warning_checks.append("Visual identity signals are thin or missing.")
        repair_actions.append("Review brand identity outputs to confirm palette and logo presence.")

    if normalized and getattr(normalized, "missing_fields", None):
        warning_checks.append("Normalized profile still has missing fields.")
        repair_actions.append("Fill the missing onboarding fields called out by normalize_input.")

    overall_status = "passed"
    if failed_checks:
        overall_status = "failed"
    elif warning_checks:
        overall_status = "warning"
    consistency_score = max(0, 100 - (len(failed_checks) * 20) - (len(warning_checks) * 5))

    report = QAReport(
        overall_status=overall_status,
        consistency_score=consistency_score,
        passed_checks=passed_checks,
        warning_checks=warning_checks,
        failed_checks=failed_checks,
        repair_actions=repair_actions,
        artifact_versions=runtime.get_artifact_versions(pack),
    )
    recommendation = recommend_repair_from_qa(report)
    report = QAReport(
        overall_status=overall_status,
        consistency_score=consistency_score,
        passed_checks=passed_checks,
        warning_checks=warning_checks,
        failed_checks=failed_checks,
        repair_actions=repair_actions,
        recommended_repair_stage=recommendation.stage_name,
        recommended_repair_reason=recommendation.reason,
        auto_repairable=recommendation.auto_repairable,
        artifact_versions=runtime.get_artifact_versions(pack),
    )
    envelope = runtime.save_artifact(
        pack,
        runtime.artifact_type,
        report,
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    pack.onboarding_answers = dict(pack.onboarding_answers or {})
    pack.onboarding_answers[runtime.input_fingerprint_key] = input_fingerprint

    if overall_status == "failed":
        message = "QA review found blocking gaps in the onboarding outputs."
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            message,
            stage_name=runtime.stage_name,
            level="error",
        )
        runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "failed",
            error=message,
            data={
                "artifact_type": runtime.artifact_type,
                "artifact_version": envelope.version,
                "overall_status": overall_status,
                "failed_checks": len(failed_checks),
                "recommended_repair_stage": report.recommended_repair_stage,
            },
        )
        raise RuntimeError(message)

    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        "QA review completed with no blockers."
        if overall_status == "passed"
        else "QA review completed with warnings for follow-up.",
        stage_name=runtime.stage_name,
    )
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={
            "artifact_type": runtime.artifact_type,
            "artifact_version": envelope.version,
            "overall_status": overall_status,
            "warning_checks": len(warning_checks),
            "recommended_repair_stage": report.recommended_repair_stage,
        },
    )
