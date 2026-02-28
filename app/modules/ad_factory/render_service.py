"""Ad Factory render service: Kling API, S3 upload, Asset creation, credits."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.storage import upload_file
from app.modules.ad_factory.kling_client import download_video, submit_text_to_video, wait_for_video
from app.modules.ad_factory.models import AdFactoryRender, RENDER_STATUS_COMPLETE, RENDER_STATUS_FAILED, RENDER_STATUS_RENDERING
from app.modules.ad_factory.services import get_render
from app.modules.creative.models import Asset
from app.modules.packs.services import get_pack_for_user
from app.modules.subscription.services import check_credits, deduct_credit

# Credits: 1 variant 10s = 1 credit; A/B/C = 3 credits
CREDITS_PER_VARIANT = 1


def render_with_kling(
    db: Session,
    render_id: UUID,
    user_id: UUID,
    variant_slots: list[str],
) -> dict:
    """
    Render selected variants via Kling, deduct credits, create Assets.
    Returns { asset_ids, credits_used }.
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

    credits_needed = len(to_render) * CREDITS_PER_VARIANT
    available = check_credits(db, user_id)
    if available < credits_needed:
        raise ValueError(
            f"Insufficient credits. Need {credits_needed}, have {available}. "
            "Upgrade or buy credits to render."
        )

    deduct_credit(db, user_id, amount=credits_needed)
    render.status = RENDER_STATUS_RENDERING
    db.commit()

    asset_ids: list[str] = []
    try:

        pack_id = render.pack_id
        for v in to_render:
            slot = v.get("slot", "A")
            kling_prompts = v.get("kling_15s") or v.get("kling_30s")
            if not kling_prompts:
                continue
            prompt = kling_prompts.get("prompt", "") if isinstance(kling_prompts, dict) else ""
            if not prompt:
                continue

            # Kling supports 5 or 10 seconds; use 10
            task_id = submit_text_to_video(prompt=prompt, duration=10, aspect_ratio="9:16")
            video_url = wait_for_video(task_id)

            video_bytes = download_video(video_url)
            key = f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.mp4"
            uploaded = upload_file(key, video_bytes, content_type="video/mp4")

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
                output_key=uploaded or key,
                srt_key=f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.srt",
                sprint_day=4,
            )
            db.add(asset)
            db.flush()
            asset_ids.append(str(asset.id))

        render.status = RENDER_STATUS_COMPLETE
        if render.render_metadata is None:
            render.render_metadata = {}
        render.render_metadata["asset_ids"] = asset_ids
        render.render_metadata["credits_used"] = credits_needed
        db.commit()
        return {"asset_ids": asset_ids, "credits_used": credits_needed}

    except Exception as e:
        render.status = RENDER_STATUS_FAILED
        render.error_message = str(e)[:2000]
        db.commit()
        raise
