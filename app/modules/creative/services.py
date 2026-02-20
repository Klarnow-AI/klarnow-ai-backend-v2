"""Creative asset services: list, get, regenerate (Version B)."""

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.creative.models import Asset
from app.modules.packs.services import get_pack_for_user


@log_service_action()
def list_assets_for_pack(db: Session, pack_id: UUID) -> list[Asset]:
    return (
        db.query(Asset)
        .filter(Asset.pack_id == pack_id)
        .order_by(Asset.created_at.desc())
        .all()
    )


@log_service_action()
def get_asset_by_id(db: Session, asset_id: UUID) -> Asset | None:
    return db.query(Asset).filter(Asset.id == asset_id).first()


@log_service_action()
def create_asset(
    db: Session,
    pack_id: UUID,
    asset_type: str,
    name: str,
    source_code: str,
    user_id: UUID,
    template_id: str | None = None,
    chat_messages: list[dict] | None = None,
) -> Asset:
    """Create a poster or flyer asset with source code. Pack must belong to user."""
    pack = get_pack_for_user(db, pack_id, user_id)
    if not pack:
        raise ValueError("Pack not found")
    if asset_type not in ("poster", "flyer"):
        raise ValueError("type must be 'poster' or 'flyer'")
    asset = Asset(
        pack_id=pack_id,
        type=asset_type,
        version="1",
        name=name,
        source_code=source_code,
        template_id=template_id,
        chat_messages=chat_messages,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@log_service_action()
def get_asset_for_pack_user(
    db: Session, asset_id: UUID, user_id: UUID
) -> Asset | None:
    asset = get_asset_by_id(db, asset_id)
    if not asset:
        return None
    pack = get_pack_for_user(db, asset.pack_id, user_id)
    return asset if pack else None


@log_service_action()
def delete_asset(db: Session, asset_id: UUID, user_id: UUID) -> None:
    """Delete an asset. Asset's pack must belong to current user."""
    asset = get_asset_for_pack_user(db, asset_id, user_id)
    if not asset:
        raise ValueError("Asset not found")
    db.delete(asset)
    db.commit()


def _next_version(existing: list[str]) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    used = {v for v in existing if len(v) == 1 and v in letters}
    for c in letters:
        if c not in used:
            return c
    return "Z1"


@log_service_action()
def regenerate_asset(db: Session, asset: Asset, user_id: UUID) -> Asset:
    """Create Version B (new asset), never overwrite. Returns the new asset."""
    pack = get_pack_for_user(db, asset.pack_id, user_id)
    if not pack:
        raise ValueError("Pack not found")
    existing_versions = [
        a.version or "1"
        for a in list_assets_for_pack(db, asset.pack_id)
        if a.type == asset.type
    ]
    new_version = _next_version(existing_versions)
    new_asset = Asset(
        pack_id=asset.pack_id,
        type=asset.type,
        version=new_version,
        name=asset.name,
        template_id=asset.template_id,
        source_code=asset.source_code,
        chat_messages=asset.chat_messages,
        script=asset.script,
        sprint_day=asset.sprint_day,
        output_key=f"assets/{asset.pack_id}/{asset.type}_{uuid.uuid4().hex[:8]}.png"
        if asset.type == "poster"
        else f"assets/{asset.pack_id}/{asset.type}_{uuid.uuid4().hex[:8]}.mp4",
        srt_key=f"assets/{asset.pack_id}/{asset.type}_{uuid.uuid4().hex[:8]}.srt"
        if asset.type == "video"
        else None,
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset
