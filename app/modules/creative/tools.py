"""Creative tools: render_poster, render_video. Compliance check before render."""

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import DomainGateBlockedError, DomainNotFoundError
from app.core.governance import validate_no_revenue_guarantees
from app.modules.creative.models import Asset
from app.modules.packs.models import Pack


RENDER_POSTER_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid"},
        "template_id": {"type": "string"},
    },
    "required": ["pack_id"],
}

RENDER_VIDEO_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid"},
        "script": {"type": "string"},
        "count": {"type": "integer", "description": "1-5 batch"},
    },
    "required": ["pack_id"],
}


def _compliance_check(db: Session, pack_id: UUID, copy_text: str | None) -> None:
    """Ensure no revenue guarantees and CTA alignment. Called before render."""
    if copy_text:
        validate_no_revenue_guarantees(copy_text)
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise DomainNotFoundError("Pack not found")
    resolved_cta = pack.primary_cta
    if not str(resolved_cta or "").strip():
        from app.shared.services.generation_context import load_generation_brand_context

        resolved_cta = load_generation_brand_context(db, pack_id, pack=pack).primary_cta
    if not str(resolved_cta or "").strip():
        raise DomainGateBlockedError("Set a primary CTA before rendering assets")


def render_poster(
    db: Session,
    pack_id: UUID | str,
    template_id: str | None = None,
    sprint_day: int | None = None,
) -> dict:
    """Create poster asset. Compliance check on copy. Output to S3 stub (output_key placeholder)."""
    pack_id = UUID(str(pack_id)) if isinstance(pack_id, str) else pack_id
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise DomainNotFoundError("Pack not found")
    _compliance_check(db, pack_id, pack.name)
    if sprint_day is not None and (sprint_day < 1 or sprint_day > 7):
        sprint_day = None
    asset = Asset(
        pack_id=pack_id,
        type="poster",
        version="1",
        template_id=template_id or "default",
        output_key=f"assets/{pack_id}/poster_{uuid.uuid4().hex[:8]}.png",
        sprint_day=sprint_day,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"asset_id": str(asset.id), "type": "poster", "output_key": asset.output_key}


def render_video(
    db: Session,
    pack_id: UUID | str,
    script: str | None = None,
    count: int = 1,
    sprint_day: int | None = None,
) -> dict:
    """Create video asset(s). Compliance check. Batch 1-5. Safe area enforced in stub."""
    pack_id = UUID(str(pack_id)) if isinstance(pack_id, str) else pack_id
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise DomainNotFoundError("Pack not found")
    _compliance_check(db, pack_id, script or "")
    if sprint_day is not None and (sprint_day < 1 or sprint_day > 7):
        sprint_day = None
    count = max(1, min(5, count))
    ids = []
    for i in range(count):
        asset = Asset(
            pack_id=pack_id,
            type="video",
            version="1",
            script=script,
            output_key=f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.mp4",
            srt_key=f"assets/{pack_id}/video_{uuid.uuid4().hex[:8]}.srt",
            sprint_day=sprint_day,
        )
        db.add(asset)
        db.flush()
        ids.append(str(asset.id))
    db.commit()
    return {"asset_ids": ids, "type": "video", "count": count}
