"""Brand OS onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import build_brand_os_artifact


@dataclass(frozen=True)
class BrandOSStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    get_existing_onboarding_brand_os: Callable[..., Any]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    get_artifact: Callable[[Any, str], Any | None]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    sync_pack_core_concept: Callable[..., None]
    compute_input_fingerprint: Callable[[Any], str]
    iso_now: Callable[[], str]
    stage_name: str
    input_fingerprint_key: str
    normalized_artifact_type: str
    artifact_type: str


def run_brand_os_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: BrandOSStageRuntime,
):
    from app.modules.brand_os.tools import generate_brand_os

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)

    existing_brand_os = runtime.get_existing_onboarding_brand_os(
        db,
        pack,
        job_id,
        expected_input_fingerprint=input_fingerprint,
    )
    if stage["status"] == "completed" or existing_brand_os:
        if existing_brand_os:
            runtime.save_artifact(
                pack,
                runtime.artifact_type,
                build_brand_os_artifact(existing_brand_os),
                source_stage=runtime.stage_name,
                timestamp=runtime.iso_now(),
                job_id=job_id,
                input_fingerprint=input_fingerprint,
            )
            pack = runtime.merge_onboarding_answers(
                db,
                pack,
                {
                    "onboarding_brand_os_id": str(existing_brand_os.id),
                    "onboarding_brand_os_job_id": job_id,
                    "onboarding_brand_os_completed_at": runtime.iso_now(),
                    runtime.input_fingerprint_key: input_fingerprint,
                },
                commit=False,
            )
            runtime.sync_pack_core_concept(pack, existing_brand_os)
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={"brand_os_id": str(existing_brand_os.id)} if existing_brand_os else None,
        )

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        "Submitting Brand OS generation with your onboarding context.",
        stage_name=runtime.stage_name,
    )
    normalized_profile = runtime.get_artifact(pack, runtime.normalized_artifact_type)
    generate_brand_os(
        db,
        pack_id,
        onboarding_answers=normalized_profile.to_brand_os_payload() if normalized_profile else None,
        source_job_id=job_id,
        progress_callback=lambda message: runtime.log_job_event(
            db,
            pack_id,
            job_id,
            message,
            stage_name=runtime.stage_name,
        ),
    )
    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    brand_os = runtime.get_existing_onboarding_brand_os(
        db,
        pack,
        job_id,
        expected_input_fingerprint=input_fingerprint,
    )
    if not brand_os:
        raise RuntimeError("Brand OS generation did not produce a result")
    runtime.save_artifact(
        pack,
        runtime.artifact_type,
        build_brand_os_artifact(brand_os),
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    pack = runtime.merge_onboarding_answers(
        db,
        pack,
        {
            "onboarding_brand_os_id": str(brand_os.id),
            "onboarding_brand_os_job_id": job_id,
            "onboarding_brand_os_completed_at": runtime.iso_now(),
            runtime.input_fingerprint_key: input_fingerprint,
        },
        commit=False,
    )
    runtime.sync_pack_core_concept(pack, brand_os)
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={"brand_os_id": str(brand_os.id), "version": brand_os.version},
    )
