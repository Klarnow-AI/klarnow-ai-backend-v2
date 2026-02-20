"""Build Launch Pack ZIP and upload to S3."""

import io
import json
import zipfile
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.core.governance import (
    check_proof_before_launch,
    validate_conversion_page_copy,
    validate_conversion_page_cta,
)
from app.core.storage import get_s3_client, upload_file, get_presigned_url
from app.modules.brand_os.models import BrandOS
from app.modules.brand_os.services import get_summary_fields
from app.modules.campaign.services import get_active_for_pack
from app.modules.conversion_page.services import get_draft, get_published
from app.modules.creative.models import Asset
from app.modules.packs.models import Pack
from app.modules.proof_vault.services import count_for_pack
from app.modules.revenue.models import Invoice, Proposal


@log_service_action()
def build_launch_pack_zip(db: Session, pack_id: UUID) -> bytes:
    """Collect pack data into a ZIP file in memory. Returns ZIP bytes."""
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise ValueError("Pack not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # Brand OS (active)
        brand_os = (
            db.query(BrandOS)
            .filter(BrandOS.pack_id == pack_id, BrandOS.is_active.is_(True))
            .first()
        )
        if brand_os:
            mission, vision, _ = get_summary_fields(brand_os)
            data = {
                "version": brand_os.version,
                "mission": mission,
                "vision": vision,
                "foundation": brand_os.foundation,
                "brand_strategy": brand_os.brand_strategy,
                "created_at": brand_os.created_at.isoformat() if brand_os.created_at else None,
            }
            zf.writestr("brand_os.json", json.dumps(data, indent=2))

        # Conversion page (published or draft structure)
        page = get_published(db, pack_id) or get_draft(db, pack_id)
        if page:
            data = {
                "version": page.version,
                "structure": page.structure,
                "seo_metadata": page.seo_metadata,
                "published_at": page.published_at.isoformat() if page.published_at else None,
            }
            zf.writestr("conversion_page.json", json.dumps(data, indent=2))

        # Proposals
        proposals = db.query(Proposal).filter(Proposal.pack_id == pack_id).order_by(Proposal.created_at.desc()).all()
        proposals_data = [
            {
                "id": str(p.id),
                "status": p.status,
                "amount": p.amount,
                "currency": p.currency,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "content": p.content,
            }
            for p in proposals
        ]
        zf.writestr("proposals.json", json.dumps(proposals_data, indent=2))

        # Invoices
        invoices = db.query(Invoice).filter(Invoice.pack_id == pack_id).order_by(Invoice.created_at.desc()).all()
        invoices_data = [
            {
                "id": str(i.id),
                "status": i.status,
                "amount": i.amount,
                "currency": i.currency,
                "due_date": i.due_date.isoformat() if i.due_date else None,
                "content": i.content,
            }
            for i in invoices
        ]
        zf.writestr("invoices.json", json.dumps(invoices_data, indent=2))

        # Assets manifest (output_key for S3 fetch)
        assets = db.query(Asset).filter(Asset.pack_id == pack_id).all()
        assets_data = [
            {
                "id": str(a.id),
                "type": a.type,
                "version": a.version,
                "output_key": a.output_key,
                "srt_key": a.srt_key,
            }
            for a in assets
        ]
        zf.writestr("assets_manifest.json", json.dumps(assets_data, indent=2))

    buf.seek(0)
    return buf.getvalue()


@log_service_action()
def build_and_upload(
    db: Session,
    pack_id: UUID,
    waiver_confirmed: bool = False,
) -> tuple[str, int]:
    """
    Run compliance, build ZIP, upload to S3, return (presigned_url, expires_in_seconds).
    Raises AppError if compliance fails.
    """
    from app.core.errors import AppError

    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise AppError("Pack not found", status_code=404)

    has_proof = count_for_pack(db, pack_id) > 0
    check_proof_before_launch(str(pack_id), has_proof=has_proof, waiver_confirmed=waiver_confirmed)

    campaign = get_active_for_pack(db, pack_id)
    page = get_published(db, pack_id) or get_draft(db, pack_id)
    if page:
        if campaign and campaign.primary_cta:
            validate_conversion_page_cta(page.structure, campaign.primary_cta)
        validate_conversion_page_copy(page.structure)

    zip_bytes = build_launch_pack_zip(db, pack_id)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"launch_packs/{pack_id}/{ts}.zip"
    client, bucket = get_s3_client()
    if not client or not bucket:
        raise AppError("Storage not configured; cannot build Launch Pack", status_code=503)
    upload_file(key, zip_bytes, content_type="application/zip")
    url = get_presigned_url(key, expires_in=3600)
    if not url:
        raise AppError("Could not generate download URL", status_code=503)
    return url, 3600
