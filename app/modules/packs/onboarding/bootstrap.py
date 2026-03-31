"""Post-onboarding bootstrap helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack

from .common import _text_or_none
from .constants import logger

def _seed_starter_videos_for_pack(db: Session, pack: Pack) -> None:
    from app.modules.creative.services import list_assets_for_pack
    from app.modules.creative.tools import render_video

    assets = list_assets_for_pack(db, pack.id)
    if any(getattr(asset, "type", None) == "video" for asset in assets):
        return

    render_video(db=db, pack_id=pack.id, count=4)


def _ensure_builder_project_for_pack(db: Session, pack: Pack) -> None:
    from app.modules.builder.services import create, get_for_pack_any

    if get_for_pack_any(db, pack.id) is not None:
        return

    project_name = _text_or_none(pack.brand_name or pack.name, limit=255) or "Website Project"
    create(db, pack.created_by_user_id, pack.id, name=project_name)


def _run_post_onboarding_bootstrap(db: Session, pack: Pack) -> None:
    try:
        _seed_starter_videos_for_pack(db, pack)
    except Exception as exc:
        logger.warning(
            "post_onboarding_video_seed_failed | pack_id=%s | error=%s",
            pack.id,
            str(exc),
        )

    _ensure_builder_project_for_pack(db, pack)
