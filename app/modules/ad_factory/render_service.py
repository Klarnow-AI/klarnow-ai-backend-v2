"""Ad Factory render jobs: provider adapter dispatch, storage, and asset creation."""

from __future__ import annotations

import logging
import secrets
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.session import SessionLocal
from app.core.storage import upload_file
from app.modules.ad_factory.kling_adapter import build_kling_request
from app.modules.ad_factory.kling_client import download_video, submit_text_to_video, wait_for_video
from app.modules.ad_factory.models import (
    AdFactoryCompile,
    AdFactoryRenderJob,
    RENDER_JOB_STATUS_COMPLETE,
    RENDER_JOB_STATUS_FAILED,
    RENDER_JOB_STATUS_PENDING,
    RENDER_JOB_STATUS_RENDERING,
    RENDER_JOB_STATUS_RESERVED,
)
from app.modules.ad_factory.schemas import (
    AdFactoryRenderJobRead,
    BillingSnapshot,
    CompileResultPayload,
    RenderScope,
)
from app.modules.ad_factory.services import get_compile, get_render_job
from app.modules.creative.models import Asset
from app.modules.creative.serializers import serialize_asset

VIDEO_CACHE_CONTROL = "public, max-age=31536000, immutable"
POSTER_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=604800"

logger = logging.getLogger(__name__)


def _serialize_asset(asset: Asset) -> dict[str, Any]:
    return serialize_asset(asset).model_dump(mode="json")


def _extract_preview_image(video_bytes: bytes) -> bytes | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return None

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = f"{temp_dir}/preview.mp4"
        output_path = f"{temp_dir}/preview.jpg"

        with open(input_path, "wb") as input_file:
            input_file.write(video_bytes)

        result = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-ss",
                "00:00:00.200",
                "-i",
                input_path,
                "-frames:v",
                "1",
                "-q:v",
                "4",
                output_path,
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Failed to generate video poster with ffmpeg: %s", result.stderr.strip())
            return None

        try:
            with open(output_path, "rb") as output_file:
                return output_file.read()
        except OSError:
            return None


def _serialize_render_job(render_job: AdFactoryRenderJob) -> AdFactoryRenderJobRead:
    return AdFactoryRenderJobRead.model_validate(
        {
            "id": render_job.id,
            "compile_result_id": render_job.compile_result_id,
            "pack_id": render_job.pack_id,
            "status": render_job.status,
            "selected_variants": render_job.selected_variants,
            "durations_requested": render_job.durations_requested,
            "voiceover_addon": render_job.voiceover_addon,
            "provider_target": render_job.provider_target,
            "provider_adapter_version": render_job.provider_adapter_version,
            "billing_snapshot": render_job.billing_snapshot,
            "provider_job_ids": render_job.provider_job_ids or {},
            "asset_urls": render_job.asset_urls or {},
            "retry_state": render_job.retry_state or {},
            "failure_state": render_job.failure_state or {},
            "render_result": render_job.render_result or {},
            "created_at": render_job.created_at,
            "updated_at": render_job.updated_at,
        }
    )


def _render_scope(
    selected_variants: list[str],
    durations_requested: list[int],
) -> RenderScope:
    variants = sorted(set(selected_variants))
    durations = sorted(set(durations_requested))
    if variants == ["A", "B", "C"] and durations == [30]:
        return "abc_bundle_30"
    if variants == ["A", "B", "C"] and durations == [15, 30]:
        return "abc_bundle_30_plus_15"
    if len(variants) == 1 and durations == [30]:
        return "single_variant_30"
    raise ValueError("Unsupported render scope. Use single_variant_30, abc_bundle_30, or abc_bundle_30_plus_15.")


def _credits_required(render_scope: RenderScope, voiceover_addon: bool) -> int:
    base = {
        "single_variant_30": 1,
        "abc_bundle_30": 3,
        "abc_bundle_30_plus_15": 5,
    }[render_scope]
    return base + (1 if voiceover_addon else 0)


def _build_billing_snapshot(
    *,
    render_scope: RenderScope,
    idempotency_key: str,
    voiceover_addon: bool,
) -> BillingSnapshot:
    settings = get_settings()
    credits_required = _credits_required(render_scope, voiceover_addon)
    if settings.ad_factory_billing_enabled:
        billing_mode = "enforced"
        credits_available = max(0, settings.ad_factory_default_credit_balance)
        purchase_required = credits_available < credits_required
        credits_reserved = 0 if purchase_required else credits_required
        reservation_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=max(1, settings.ad_factory_credit_reservation_minutes))
            if credits_reserved
            else None
        )
    else:
        billing_mode = "feature_flagged"
        credits_available = credits_required
        purchase_required = False
        credits_reserved = 0
        reservation_expires_at = None
    return BillingSnapshot(
        billing_mode=billing_mode,  # type: ignore[arg-type]
        render_scope=render_scope,
        credits_required=credits_required,
        credits_available=credits_available,
        credits_reserved=credits_reserved,
        credits_consumed=0,
        purchase_required=purchase_required,
        reservation_expires_at=reservation_expires_at,
        idempotency_key=idempotency_key,
    )


def finalize_render_storage(render_job_id: str, jobs: list[dict[str, str]]) -> None:
    db = SessionLocal()
    try:
        render_job = db.get(AdFactoryRenderJob, UUID(render_job_id))
        if not render_job:
            logger.error("Render job %s missing during storage finalization", render_job_id)
            return

        errors: list[str] = []
        asset_urls = dict(render_job.asset_urls or {})
        for job in jobs:
            asset = db.get(Asset, UUID(job["asset_id"]))
            if not asset:
                errors.append(f"Asset {job['asset_id']} missing during storage finalization")
                continue

            try:
                video_bytes = download_video(job["source_url"])
                uploaded = upload_file(
                    job["output_key"],
                    video_bytes,
                    content_type="video/mp4",
                    cache_control=VIDEO_CACHE_CONTROL,
                )
                if not uploaded:
                    raise ValueError("Storage is not configured for rendered video uploads")

                asset.output_key = uploaded

                poster_bytes = _extract_preview_image(video_bytes)
                if poster_bytes:
                    poster_uploaded = upload_file(
                        job["poster_key"],
                        poster_bytes,
                        content_type="image/jpeg",
                        cache_control=POSTER_CACHE_CONTROL,
                    )
                    if poster_uploaded:
                        asset.preview_image_key = poster_uploaded

                asset.preview_url = None
                db.flush()
                asset_urls[str(asset.id)] = _serialize_asset(asset).get("output_url")
            except Exception as exc:
                logger.exception("Failed to finalize asset %s for render job %s", job["asset_id"], render_job_id)
                errors.append(str(exc))

        render_result = dict(render_job.render_result or {})
        render_result["storage_sync_status"] = "failed" if errors else "complete"
        if errors:
            render_result["storage_sync_errors"] = errors[:5]
        render_job.render_result = render_result
        render_job.asset_urls = asset_urls
        if errors:
            render_job.error_message = "; ".join(errors)[:2000]
        db.commit()
    finally:
        db.close()


def create_render_job(
    db: Session,
    *,
    compile_id: UUID,
    user_id: UUID,
    selected_variants: list[str],
    durations_requested: list[int],
    voiceover_addon: bool = False,
    provider_target: str = "kling",
    idempotency_key: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> AdFactoryRenderJobRead:
    compile_record = get_compile(db, compile_id, user_id)
    if not compile_record:
        raise ValueError("Compile result not found")

    compile_payload = CompileResultPayload.model_validate(compile_record.compile_result)
    validator_status = str((compile_record.validator_result or {}).get("status") or "")
    if validator_status != "pass":
        raise ValueError("Render is blocked until validation passes")
    if provider_target != "kling":
        raise ValueError("Only Kling is supported in this implementation")

    selected = sorted(set(selected_variants))
    durations = sorted(set(durations_requested))
    render_scope = _render_scope(selected, durations)
    job_idempotency_key = (idempotency_key or secrets.token_hex(12)).strip()
    if not job_idempotency_key:
        raise ValueError("Idempotency key is required")

    existing = (
        db.query(AdFactoryRenderJob)
        .filter(
            AdFactoryRenderJob.compile_result_id == compile_id,
            AdFactoryRenderJob.idempotency_key == job_idempotency_key,
        )
        .order_by(AdFactoryRenderJob.created_at.desc())
        .first()
    )
    if existing:
        return _serialize_render_job(existing)

    billing_snapshot = _build_billing_snapshot(
        render_scope=render_scope,
        idempotency_key=job_idempotency_key,
        voiceover_addon=voiceover_addon,
    )
    if billing_snapshot.purchase_required:
        raise ValueError("Insufficient credits for this render scope")

    render_job = AdFactoryRenderJob(
        compile_result_id=compile_record.id,
        pack_id=compile_record.pack_id,
        status=RENDER_JOB_STATUS_RESERVED if billing_snapshot.credits_reserved else RENDER_JOB_STATUS_PENDING,
        selected_variants=selected,
        durations_requested=durations,
        voiceover_addon=voiceover_addon,
        provider_target=provider_target,
        provider_adapter_version=str((compile_record.versions or {}).get("provider_adapter_version") or "kling-adapter-1"),
        billing_snapshot=billing_snapshot.model_dump(mode="json"),
        idempotency_key=job_idempotency_key,
        provider_job_ids={},
        asset_urls={},
        retry_state={"retryable": True, "attempts": 0},
        failure_state={},
        render_result={
            "render_scope": render_scope,
            "assets": [],
            "asset_ids": [],
            "provider_payloads": {},
        },
    )
    db.add(render_job)
    db.flush()

    render_job.status = RENDER_JOB_STATUS_RENDERING

    asset_ids: list[str] = []
    rendered_assets: list[dict[str, Any]] = []
    provider_job_ids: dict[str, str] = {}
    provider_payloads: dict[str, dict[str, Any]] = {}
    background_jobs: list[dict[str, str]] = []
    try:
        variants = compile_payload.variants.as_dict()
        for slot in selected:
            variant = variants[slot]  # type: ignore[index]
            for duration in durations:
                intent = variant.render_intent_15s if duration == 15 else variant.render_intent_30s
                kling_request = build_kling_request(intent)
                task_id = submit_text_to_video(
                    prompt=str(kling_request["prompt"]),
                    duration=int(kling_request["duration"]),
                    aspect_ratio=str(kling_request["aspect_ratio"]),
                )
                video_url = wait_for_video(task_id)
                asset = Asset(
                    pack_id=compile_record.pack_id,
                    type="video",
                    version="1",
                    script=intent.spoken_narration[:8000],
                    output_key=None,
                    preview_url=video_url,
                    srt_key=f"assets/{compile_record.pack_id}/video_{uuid.uuid4().hex[:8]}.srt",
                    sprint_day=4,
                )
                db.add(asset)
                db.flush()

                asset_ids.append(str(asset.id))
                rendered_assets.append(_serialize_asset(asset))
                render_key = f"{slot}_{duration}"
                provider_job_ids[render_key] = task_id
                provider_payloads[render_key] = {
                    "provider_target": provider_target,
                    "request": kling_request,
                    "requested_duration_seconds": duration,
                }
                background_jobs.append(
                    {
                        "asset_id": str(asset.id),
                        "source_url": video_url,
                        "output_key": f"assets/{compile_record.pack_id}/video_{uuid.uuid4().hex[:8]}.mp4",
                        "poster_key": f"assets/{compile_record.pack_id}/video_{uuid.uuid4().hex[:8]}.jpg",
                    }
                )

        billing_data = dict(render_job.billing_snapshot or {})
        billing_data["credits_consumed"] = int(billing_data.get("credits_reserved") or 0)
        render_job.billing_snapshot = billing_data
        render_job.provider_job_ids = provider_job_ids
        render_job.render_result = {
            "render_scope": render_scope,
            "asset_ids": asset_ids,
            "assets": rendered_assets,
            "provider_payloads": provider_payloads,
            "storage_sync_status": "pending" if background_jobs else "complete",
        }
        render_job.status = RENDER_JOB_STATUS_COMPLETE
        db.commit()
        db.refresh(render_job)
        if background_jobs:
            if background_tasks is not None:
                background_tasks.add_task(finalize_render_storage, str(render_job.id), background_jobs)
            else:
                finalize_render_storage(str(render_job.id), background_jobs)
        return _serialize_render_job(render_job)
    except Exception as exc:
        render_job.status = RENDER_JOB_STATUS_FAILED
        render_job.error_message = str(exc)[:2000]
        render_job.failure_state = {
            "message": str(exc)[:500],
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        retry_state = dict(render_job.retry_state or {})
        retry_state["attempts"] = int(retry_state.get("attempts") or 0) + 1
        render_job.retry_state = retry_state
        db.commit()
        raise


def read_render_job(db: Session, render_job_id: UUID, user_id: UUID) -> AdFactoryRenderJobRead | None:
    render_job = get_render_job(db, render_job_id, user_id)
    if not render_job:
        return None
    return _serialize_render_job(render_job)
