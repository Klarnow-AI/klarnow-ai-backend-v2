"""Ad Factory render service: Kling API, S3 upload, and Asset creation."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import uuid
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.db.session import SessionLocal
from app.core.storage import get_asset_url, upload_file
from app.modules.ad_factory.kling_client import download_video, submit_text_to_video, wait_for_video
from app.modules.ad_factory.models import (
    AdFactoryRender,
    RENDER_STATUS_COMPLETE,
    RENDER_STATUS_FAILED,
    RENDER_STATUS_RENDERING,
)
from app.modules.ad_factory.services import get_render
from app.modules.creative.models import Asset

ASSET_URL_TTL_SECONDS = 86400
VIDEO_CACHE_CONTROL = "public, max-age=31536000, immutable"
POSTER_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=604800"

logger = logging.getLogger(__name__)


def _serialize_rendered_asset(asset: Asset) -> dict[str, Any]:
    output_key = asset.output_key
    return {
        "id": str(asset.id),
        "pack_id": str(asset.pack_id),
        "type": asset.type,
        "version": asset.version,
        "name": asset.name,
        "template_id": asset.template_id,
        "source_code": asset.source_code,
        "output_key": output_key,
        "output_url": (
            get_asset_url(output_key, expires_in=ASSET_URL_TTL_SECONDS)
            if output_key
            else asset.preview_url
        ),
        "poster_url": (
            get_asset_url(asset.preview_image_key, expires_in=ASSET_URL_TTL_SECONDS)
            if asset.preview_image_key
            else None
        ),
        "script": asset.script,
        "srt_key": asset.srt_key,
        "sprint_day": asset.sprint_day,
        "chat_messages": asset.chat_messages,
        "created_at": asset.created_at.isoformat(),
    }


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


def finalize_render_storage(render_id: str, jobs: list[dict[str, str]]) -> None:
    db = SessionLocal()
    try:
        render = db.get(AdFactoryRender, UUID(render_id))
        if not render:
            logger.error("Render %s missing during storage finalization", render_id)
            return

        errors: list[str] = []
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
            except Exception as exc:
                logger.exception("Failed to finalize asset %s for render %s", job["asset_id"], render_id)
                errors.append(str(exc))

        if render.render_metadata is None:
            render.render_metadata = {}
        render.render_metadata["storage_sync_status"] = "failed" if errors else "complete"
        if errors:
            render.render_metadata["storage_sync_errors"] = errors[:5]
            render.error_message = "; ".join(errors)[:2000]
        else:
            render.render_metadata.pop("storage_sync_errors", None)
        db.commit()
    finally:
        db.close()


def render_with_kling(
    db: Session,
    render_id: UUID,
    user_id: UUID,
    variant_slots: list[str],
    background_tasks: BackgroundTasks | None = None,
) -> dict:
    """
    Render selected variants via Kling and create Assets.
    Returns { asset_ids }.
    """
    render = get_render(db, render_id, user_id)
    if not render:
        raise ValueError("Render not found")
    if render.status not in ("validated", "draft"):
        raise ValueError(f"Render cannot be rendered; status={render.status}")

    variants = render.variants
    if not variants:
        raise ValueError("No variants in render")

    # Filter to requested slots
    slot_set = set(variant_slots)
    to_render = [v for v in variants if v.get("slot") in slot_set]
    if not to_render:
        raise ValueError("No valid variant slots selected")

    render.status = RENDER_STATUS_RENDERING
    db.commit()

    asset_ids: list[str] = []
    rendered_assets: list[dict[str, Any]] = []
    background_jobs: list[dict[str, str]] = []
    try:
        pack_id = render.pack_id
        for v in to_render:
            kling_prompts = v.get("kling_15s") or v.get("kling_30s")
            if not kling_prompts:
                continue
            prompt = kling_prompts.get("prompt", "") if isinstance(kling_prompts, dict) else ""
            if not prompt:
                continue

            # Kling supports 5 or 10 seconds; use 10
            task_id = submit_text_to_video(prompt=prompt, duration=10, aspect_ratio="9:16")
            video_url = wait_for_video(task_id)
            video_key = f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.mp4"
            poster_key = f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.jpg"

            script_parts = []
            script_30s = v.get("script_30s", {})
            if isinstance(script_30s, dict) and script_30s.get("beats"):
                script_parts = [b.get("text", "") for b in script_30s["beats"] if b.get("text")]
            script_text = " ".join(script_parts)[:8000] if script_parts else prompt[:8000]

            asset = Asset(
                pack_id=pack_id,
                type="video",
                version="1",
                script=script_text,
                output_key=None,
                preview_url=video_url,
                srt_key=f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.srt",
                sprint_day=4,
            )
            db.add(asset)
            db.flush()
            asset_ids.append(str(asset.id))
            rendered_assets.append(_serialize_rendered_asset(asset))
            background_jobs.append(
                {
                    "asset_id": str(asset.id),
                    "source_url": video_url,
                    "output_key": video_key,
                    "poster_key": poster_key,
                }
            )

        render.status = RENDER_STATUS_COMPLETE
        if render.render_metadata is None:
            render.render_metadata = {}
        render.render_metadata["asset_ids"] = asset_ids
        render.render_metadata["rendered_variant_slots"] = [
            v.get("slot") for v in to_render if v.get("slot")
        ]
        render.render_metadata["storage_sync_status"] = "pending" if background_jobs else "complete"
        db.commit()
        if background_jobs:
            if background_tasks is not None:
                background_tasks.add_task(finalize_render_storage, str(render.id), background_jobs)
            else:
                finalize_render_storage(str(render.id), background_jobs)
        return {"asset_ids": asset_ids, "assets": rendered_assets}

    except Exception as e:
        render.status = RENDER_STATUS_FAILED
        render.error_message = str(e)[:2000]
        db.commit()
        raise
