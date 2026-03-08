"""Creative asset services: list, get, regenerate (Version B)."""

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.creative.models import Asset
from app.modules.packs.models import Pack


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
    template_id: str | None = None,
    chat_messages: list[dict] | None = None,
) -> Asset:
    """Create a poster or flyer asset with source code."""
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
    return asset


@log_service_action()
def get_asset_for_pack_user(
    db: Session, asset_id: UUID, user_id: UUID
) -> Asset | None:
    return (
        db.query(Asset)
        .join(Pack, Pack.id == Asset.pack_id)
        .filter(
            Asset.id == asset_id,
            Pack.created_by_user_id == user_id,
        )
        .first()
    )


@log_service_action()
def delete_asset(db: Session, asset: Asset) -> None:
    """Delete an asset."""
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
def regenerate_asset(db: Session, asset: Asset) -> Asset:
    """Create Version B (new asset), never overwrite. Returns the new asset."""
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
    return new_asset
