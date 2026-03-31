"""Packs API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import BadRequestError, NotFoundError
from app.modules.brand_os.schemas import brand_os_read_from_orm
from app.modules.brand_os.services import get_by_id_and_pack as get_brand_os_by_id_and_pack
from app.modules.brand_os.services import get_by_source_job_id as get_brand_os_by_source_job_id
from app.modules.brand_os.services import get_summary_fields as get_brand_os_summary_fields
from app.modules.brand_os.tools import generate_brand_os
from app.modules.packs.models import Pack, User
from app.core.storage import upload_file as storage_upload_file, get_asset_url
from app.modules.packs.schemas import (
    DayReadinessResponse,
    PackCreate,
    PackList,
    PackListItem,
    PackPatch,
    PackRead,
    PackSummaryResponse,
    BrandOSSummary,
    CampaignSummary,
    WebsiteSummary,
    PlanTrackerSummary,
    LeadsSummary,
    ProposalsSummary,
    InvoicesSummary,
    OnboardingSubmit,
    OnboardingCompleteAccepted,
    OnboardingArtifactLineageResponse,
    OnboardingJobStatusResponse,
    OnboardingRepairFromQARequest,
    OnboardingRepairRequest,
    ExtractBrandBody,
    ExtractBrandResponse,
    GenerateStarterBrandBody,
    GenerateStarterBrandResponse,
    GenerateLogoBody,
    GenerateLogoResponse,
    UploadLogoResponse,
    SuggestTypographyBody,
    SuggestTypographyResponse,
    SuggestPaletteBody,
    SuggestPaletteResponse,
)
from app.modules.packs.services import (
    archive_pack,
    append_suggested_logo,
    append_suggested_logos,
    build_onboarding_context,
    build_step_2_finalization_payload,
    complete_onboarding,
    create_pack,
    delete_pack,
    extract_palette_from_answers,
    fingerprint_payload,
    get_pack_for_user,
    get_step_2_finalization_cache,
    list_packs_for_user,
    merge_onboarding_answers,
    resolve_pack_vibe_chips,
    restore_pack,
    set_step_2_finalization_cache,
    submit_onboarding,
    sync_pack_target_audience,
)
from app.modules.packs.onboarding_services import extract_brand, generate_starter_brand
from app.modules.packs.logo_generation import (
    generate_logo,
    get_logo_primary_asset_url,
    get_logo_variant_urls,
)
from app.modules.packs.brand_identity_suggestions import suggest_typography, suggest_palette
from app.modules.packs.onboarding.public import (
    dispatch_onboarding_job_from_api,
    enqueue_onboarding_qa_repair,
    enqueue_onboarding_stage_repair,
    get_onboarding_artifact_lineage,
    enqueue_onboarding_job,
    get_onboarding_job_status,
    request_onboarding_job_pause,
    resume_onboarding_job,
    run_onboarding_job,
)

router = APIRouter()


@router.get("", response_model=PackList)
def list_my_packs(
    include_archived: bool = Query(False, description="Include archived packs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List projects for the authenticated user."""
    packs = list_packs_for_user(db, current_user.id, include_archived=include_archived)
    items = [PackListItem(**PackRead.model_validate(p).model_dump()) for p in packs]
    return PackList(items=items, total=len(items))


@router.post("", response_model=PackRead, status_code=status.HTTP_201_CREATED)
def create_pack_route(
    body: PackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new pack for the authenticated user."""
    pack_type = body.pack_type if body.pack_type in ("enquiries", "quotes", "sales") else "enquiries"
    pack = create_pack(db, current_user.id, name=body.name, pack_type=pack_type)
    return PackRead.model_validate(pack)


@router.get("/{pack_id}/summary", response_model=PackSummaryResponse)
def get_pack_summary(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full project overview: Brand OS through generated assets."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    from app.modules.brand_os.models import BrandOS
    from app.modules.builder.models import BuilderProject
    from app.modules.docs.models import Document
    from app.modules.creative.models import Asset

    meta = db.execute(
        select(
            select(BrandOS.id)
                .where(BrandOS.pack_id == pack_id, BrandOS.is_active.is_(True))
                .limit(1)
                .scalar_subquery()
                .label("brand_os_id"),
            select(BrandOS.brand_strategy)
                .where(BrandOS.pack_id == pack_id, BrandOS.is_active.is_(True))
                .limit(1)
                .scalar_subquery()
                .label("brand_strategy"),
            select(BuilderProject.live_url)
                .where(
                    BuilderProject.pack_id == pack_id,
                    BuilderProject.published_at.isnot(None),
                    BuilderProject.live_url.isnot(None),
                )
                .order_by(BuilderProject.published_at.desc())
                .limit(1)
                .scalar_subquery()
                .label("site_live_url"),
            select(BuilderProject.published_at)
                .where(
                    BuilderProject.pack_id == pack_id,
                    BuilderProject.published_at.isnot(None),
                    BuilderProject.live_url.isnot(None),
                )
                .order_by(BuilderProject.published_at.desc())
                .limit(1)
                .scalar_subquery()
                .label("site_published_at"),
        )
    ).one()._mapping

    has_brand_os = meta["brand_os_id"] is not None
    brand_strategy = meta["brand_strategy"]
    if has_brand_os and brand_strategy and isinstance(brand_strategy, dict):
        bs = brand_strategy
        mv = bs.get("mission_vision") or {}
        mission = mv.get("mission")
        vision = mv.get("vision")
        pos = bs.get("positioning_differentiation") or {}
        has_positioning = bool(pos.get("statement") or pos.get("unique_advantage"))
    else:
        mission, vision, has_positioning = None, None, False

    primary_cta = (pack.primary_cta or "").strip() or None
    has_site = meta["site_live_url"] is not None
    counts = (
        db.execute(
            select(
                select(func.count(Document.id))
                .where(Document.pack_id == pack_id, Document.type == "proposal")
                .scalar_subquery()
                .label("proposals_total"),
                select(func.count(Document.id))
                .where(
                    Document.pack_id == pack_id,
                    Document.type == "proposal",
                    Document.status == "sent",
                )
                .scalar_subquery()
                .label("proposals_sent"),
                select(func.count(Document.id))
                .where(
                    Document.pack_id == pack_id,
                    Document.type == "proposal",
                    Document.status == "accepted",
                )
                .scalar_subquery()
                .label("proposals_accepted"),
                select(func.count(Document.id))
                .where(
                    Document.pack_id == pack_id,
                    Document.type == "proposal",
                    Document.status == "__declined__",
                )
                .scalar_subquery()
                .label("proposals_declined"),
                select(func.count(Document.id))
                .where(Document.pack_id == pack_id, Document.type == "invoice")
                .scalar_subquery()
                .label("invoices_total"),
                select(func.count(Document.id))
                .where(
                    Document.pack_id == pack_id,
                    Document.type == "invoice",
                    Document.status == "sent",
                )
                .scalar_subquery()
                .label("invoices_sent"),
                select(func.count(Document.id))
                .where(
                    Document.pack_id == pack_id,
                    Document.type == "invoice",
                    Document.status == "paid",
                )
                .scalar_subquery()
                .label("invoices_paid"),
                select(func.count(Document.id))
                .where(
                    Document.pack_id == pack_id,
                    Document.type == "invoice",
                    Document.status == "__overdue__",
                )
                .scalar_subquery()
                .label("invoices_overdue"),
                select(func.count(Asset.id))
                .where(Asset.pack_id == pack_id)
                .scalar_subquery()
                .label("assets_count"),
            )
        )
        .one()
        ._mapping
    )

    return PackSummaryResponse(
        pack=PackRead.model_validate(pack),
        brand_os=BrandOSSummary(
            mission=mission,
            vision=vision,
            has_positioning=has_positioning,
        ) if has_brand_os else None,
        campaign=CampaignSummary(
            primary_cta=primary_cta,
            goal_summary=(pack.core_concept or "")[:200] or None,
        ) if primary_cta else None,
        website=WebsiteSummary(
            live_url=meta["site_live_url"],
            published_at=meta["site_published_at"].isoformat() if meta["site_published_at"] else None,
        ) if has_site else None,
        plan_tracker=None,
        leads=LeadsSummary(),
        proposals=ProposalsSummary(
            total=int(counts["proposals_total"] or 0),
            sent=int(counts["proposals_sent"] or 0),
            accepted=int(counts["proposals_accepted"] or 0),
            declined=int(counts["proposals_declined"] or 0),
        ),
        invoices=InvoicesSummary(
            total=int(counts["invoices_total"] or 0),
            sent=int(counts["invoices_sent"] or 0),
            paid=int(counts["invoices_paid"] or 0),
            overdue=int(counts["invoices_overdue"] or 0),
        ),
        assets_count=int(counts["assets_count"] or 0),
    )

@router.get("/{pack_id}/day-readiness", response_model=DayReadinessResponse)
def get_day_readiness(
    pack_id: UUID,
    day: int = Query(..., ge=0, le=3, description="Day number (0-3)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return whether the pack has enough onboarding information to continue."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    _ = day
    answers = pack.onboarding_answers or {}
    required_fields = (
        "what_do_you_do",
        "why_started",
        "who_are_your_customers",
        "primary_cta",
    )
    ready = all(str(answers.get(field) or "").strip() for field in required_fields)
    return DayReadinessResponse(ready=ready)


@router.get("/{pack_id}", response_model=PackRead)
def get_pack(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a pack by id (must belong to current user)."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    return PackRead.model_validate(pack)


@router.patch("/{pack_id}", response_model=PackRead)
def patch_pack(
    pack_id: UUID,
    body: PackPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update project foundation and onboarding fields."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    from datetime import datetime, timezone
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        pack.name = data["name"]
    if "pack_type" in data and data["pack_type"] in ("enquiries", "quotes", "sales"):
        pack.pack_type = data["pack_type"]
    if "core_concept" in data:
        pack.core_concept = data["core_concept"] if data["core_concept"] else None
    day0_fields = ("brand_name", "primary_cta", "usp_category", "usp_statement", "usp_proof", "usp_locked_line", "proof_types", "proof_text")
    day13_fields = ("offer_one_liner", "target_audience", "primary_pain", "primary_outcome", "hero_angle")
    for key in day0_fields + day13_fields:
        if key in data:
            setattr(pack, key, data[key])
    if "onboarding_answers" in data and data["onboarding_answers"]:
        pack = merge_onboarding_answers(
            db,
            pack,
            data["onboarding_answers"],
            commit=False,
        )
    
    # Day 0 completion check
    was_day_0_incomplete = pack.day_0_completed_at is None
    if was_day_0_incomplete:
        bn = (pack.brand_name or "").strip()
        cta = (pack.primary_cta or "").strip()
        usp = (pack.usp_statement or "").strip()
        if bn and cta and usp:
            pack.day_0_completed_at = datetime.now(timezone.utc)
    
    db.commit()
    return PackRead.model_validate(pack)


@router.post("/{pack_id}/archive", response_model=PackRead)
def archive_pack_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a pack."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    return PackRead.model_validate(archive_pack(db, pack))


@router.post("/{pack_id}/restore", response_model=PackRead)
def restore_pack_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore an archived pack."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    if pack.status != "archived":
        from app.core.errors import BadRequestError
        raise BadRequestError("Pack is not archived")
    return PackRead.model_validate(restore_pack(db, pack))


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pack_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a pack and all related data."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    delete_pack(db, pack)
    return None


@router.post("/{pack_id}/onboarding", response_model=PackRead)
def submit_onboarding_route(
    pack_id: UUID,
    body: OnboardingSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit onboarding answers (max 6)."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    return PackRead.model_validate(submit_onboarding(db, pack, body.answers))


def _run_onboarding_background(pack_id: UUID) -> None:
    """Compatibility wrapper for callers still referencing old function name."""
    raise RuntimeError(
        "In-process onboarding workers were removed. Enqueue via dispatch_onboarding_job_from_api()."
    )


def _require_step_2_finalization_ready(db: Session, pack: Pack) -> None:
    del db
    answers = pack.onboarding_answers or {}
    required_fields = (
        ("what_do_you_do", "Tell us what you do before completing onboarding."),
        ("why_started", "Share why you started it before completing onboarding."),
        (
            "who_are_your_customers",
            "Tell us who your customers are before completing onboarding.",
        ),
        ("primary_cta", "Tell us what you want people to do before completing onboarding."),
    )
    for key, message in required_fields:
        if str(answers.get(key) or "").strip():
            continue
        raise BadRequestError(message)

    if answers.get("has_existing_brand") not in {"yes", "no"}:
        raise BadRequestError(
            "Tell us whether you already have a logo or website before completing onboarding."
        )

    has_existing_brand = answers.get("has_existing_brand") == "yes"
    if has_existing_brand:
        has_brand_input = any(
            str(answers.get(key) or "").strip()
            for key in ("brand_url", "wordmark_svg_or_url", "generated_logo_url", "extracted_brand")
        )
        if not has_brand_input:
            raise BadRequestError(
                "Add your website URL or upload a logo before completing onboarding."
            )
        return

    if not str(answers.get("brand_name") or "").strip():
        raise BadRequestError("Add your brand name before completing onboarding.")

    raw_vibe = answers.get("vibe_chips")
    if isinstance(raw_vibe, list):
        has_vibes = any(str(item).strip() for item in raw_vibe)
    else:
        has_vibes = str(raw_vibe or "").strip() not in {"", "[]"}
    if not has_vibes:
        raise BadRequestError("Pick a brand vibe before completing onboarding.")


def _build_brand_os_summary_text(brand_os_row) -> str:
    mission, vision, _has_positioning = get_brand_os_summary_fields(brand_os_row)
    foundation = brand_os_row.foundation if isinstance(brand_os_row.foundation, dict) else {}
    summary_parts: list[str] = []
    brand_name = foundation.get("brand_name")
    one_line_offer = foundation.get("one_line_offer")
    brand_industry = foundation.get("brand_industry")
    main_audience = foundation.get("main_audience")

    if brand_name:
        summary_parts.append(f"Brand: {brand_name}")
    if mission:
        summary_parts.append(f"Mission: {mission}")
    if vision:
        summary_parts.append(f"Vision: {vision}")
    if one_line_offer:
        summary_parts.append(f"Offer: {one_line_offer}")
    if brand_industry:
        summary_parts.append(f"Industry: {brand_industry}")
    if isinstance(main_audience, list) and main_audience:
        audience_text = ", ".join(str(item).strip() for item in main_audience if str(item).strip())
        if audience_text:
            summary_parts.append(f"Audience: {audience_text}")
    return ". ".join(summary_parts)


def _resolve_brand_os_id(value) -> UUID | None:
    """Accept tool payloads or ORM-like rows and normalize to a Brand OS UUID."""
    raw_id = None
    if isinstance(value, dict):
        raw_id = value.get("brand_os_id") or value.get("id")
    else:
        raw_id = getattr(value, "id", None)
    if raw_id is None:
        return None
    try:
        return UUID(str(raw_id))
    except (TypeError, ValueError, AttributeError):
        return None


@router.post(
    "/{pack_id}/onboarding/complete",
    response_model=OnboardingCompleteAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def complete_onboarding_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark onboarding complete and kick off the background onboarding pipeline."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    _require_step_2_finalization_ready(db, pack)
    answers = pack.onboarding_answers or {}
    sync_pack_target_audience(pack)
    complete_onboarding(db, pack, answers=answers, commit=False)
    job = enqueue_onboarding_job(db, pack_id)
    db.commit()
    db.refresh(pack)

    job_id = str(job.get("job_id") or "")
    try:
        dispatch_onboarding_job_from_api(pack_id, job_id)
    except Exception:
        result = run_onboarding_job(pack_id, job_id)
        while result.retry:
            result = run_onboarding_job(pack_id, job_id)

    payload = OnboardingCompleteAccepted(
        status="processing",
        pack_id=str(pack_id),
        job_id=job_id or None,
    )
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload.model_dump())


@router.get("/{pack_id}/onboarding/status", response_model=OnboardingJobStatusResponse)
def onboarding_status_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get onboarding background-job status for polling and retry visibility."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    return OnboardingJobStatusResponse(**get_onboarding_job_status(pack))


@router.get("/{pack_id}/onboarding/artifacts", response_model=OnboardingArtifactLineageResponse)
def onboarding_artifact_lineage_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest typed onboarding artifacts and their lineage metadata."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    return OnboardingArtifactLineageResponse(items=get_onboarding_artifact_lineage(pack))


@router.post("/{pack_id}/onboarding/repair", response_model=OnboardingJobStatusResponse)
def repair_onboarding_route(
    pack_id: UUID,
    body: OnboardingRepairRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Queue a bounded onboarding repair run from the requested stage onward."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    try:
        job = enqueue_onboarding_stage_repair(
            db,
            pack_id,
            stage_name=body.stage,
            include_downstream=body.include_downstream,
            reason=body.reason,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    db.commit()
    db.refresh(pack)

    job_id = str(job.get("job_id") or "")
    if job_id:
        try:
            dispatch_onboarding_job_from_api(pack_id, job_id)
        except Exception:
            result = run_onboarding_job(pack_id, job_id)
            while result.retry:
                result = run_onboarding_job(pack_id, job_id)
        db.refresh(pack)
    return OnboardingJobStatusResponse(**get_onboarding_job_status(pack))


@router.post("/{pack_id}/onboarding/repair-from-qa", response_model=OnboardingJobStatusResponse)
def repair_onboarding_from_qa_route(
    pack_id: UUID,
    body: OnboardingRepairFromQARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Queue the smallest repairable onboarding rerun from the latest QA report."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    try:
        job = enqueue_onboarding_qa_repair(
            db,
            pack_id,
            include_downstream=body.include_downstream,
            reason=body.reason,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    db.commit()
    db.refresh(pack)

    job_id = str(job.get("job_id") or "")
    if job_id:
        try:
            dispatch_onboarding_job_from_api(pack_id, job_id)
        except Exception:
            result = run_onboarding_job(pack_id, job_id)
            while result.retry:
                result = run_onboarding_job(pack_id, job_id)
        db.refresh(pack)
    return OnboardingJobStatusResponse(**get_onboarding_job_status(pack))


@router.post("/{pack_id}/onboarding/stop", response_model=OnboardingJobStatusResponse)
def stop_onboarding_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request a safe pause for the durable onboarding background job."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    status_payload = request_onboarding_job_pause(db, pack_id)
    return OnboardingJobStatusResponse(**status_payload)


@router.post("/{pack_id}/onboarding/continue", response_model=OnboardingJobStatusResponse)
def continue_onboarding_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused onboarding background job or clear a pending stop request."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    status_payload = resume_onboarding_job(db, pack_id)
    job_id = str(status_payload.get("job_id") or "")
    if status_payload.get("status") == "queued" and job_id:
        try:
            dispatch_onboarding_job_from_api(pack_id, job_id)
        except Exception:
            result = run_onboarding_job(pack_id, job_id)
            while result.retry:
                result = run_onboarding_job(pack_id, job_id)
        db.refresh(pack)
        status_payload = get_onboarding_job_status(pack)

    return OnboardingJobStatusResponse(**status_payload)


@router.post("/{pack_id}/onboarding/extract-brand", response_model=ExtractBrandResponse)
async def extract_brand_route(
    pack_id: UUID,
    body: ExtractBrandBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract brand profile from URL, pasted text, or logo with rich metadata."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    result = await extract_brand(
        input_type=body.input_type,
        url=body.url,
        pasted_text=body.pasted_text,
        logo_file_key=body.logo_file_key,
    )
    return ExtractBrandResponse(
        brand_name=result.get("brand_name", "My Brand"),
        offer_cues=result.get("offer_cues", []),
        tagline=result.get("tagline"),
        description=result.get("description"),
        industry=result.get("industry"),
        contact_info=result.get("contact_info", {}),
        social_links=result.get("social_links", []),
        logo_url=result.get("logo_url"),
        color_candidates=result.get("color_candidates", []),
        raw_extract=result.get("raw_extract"),
    )


@router.post("/{pack_id}/onboarding/generate-starter-brand", response_model=GenerateStarterBrandResponse)
def generate_starter_brand_route(
    pack_id: UUID,
    body: GenerateStarterBrandBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI logo image and palette from brand name and vibe chips."""
    from app.core.errors import AppError
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    answers = pack.onboarding_answers or {}
    if answers.get("has_existing_brand") == "no" and pack.onboarding_completed_at is None:
        raise AppError(
            "Complete Day 0 onboarding before generating brand identity for new brands.",
            status_code=400,
        )
    result = generate_starter_brand(
        brand_name=body.brand_name,
        vibe_chips=body.vibe_chips or [],
        pack_id=str(pack_id),
    )
    wordmark = result["wordmark_svg_or_url"]
    pack = append_suggested_logos(
        db,
        pack,
        get_logo_variant_urls(result) or [wordmark],
        commit=False,
    )
    pack = merge_onboarding_answers(
        db,
        pack,
        {
            "wordmark_svg_or_url": wordmark,
            "generated_logo_url": result.get("logo_url"),
            "transparent_logo_url": result.get("transparent_logo_url"),
            "palette": result["palette"],
        },
        commit=False,
    )
    db.commit()
    return GenerateStarterBrandResponse(
        wordmark_svg_or_url=wordmark,
        palette=result["palette"],
        logo_url=result.get("logo_url"),
        transparent_logo_url=result.get("transparent_logo_url"),
    )


@router.post("/{pack_id}/onboarding/upload-logo", response_model=UploadLogoResponse)
async def upload_logo_route(
    pack_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a logo file; merge into onboarding_answers and append to suggested_logos."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    content = await file.read()
    if not content:
        from app.core.errors import AppError
        raise AppError("File is empty", status_code=400)
    import uuid as u
    ext = "png"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() or "png"
    if ext == "svg" or (file.content_type and "svg" in file.content_type.lower()):
        raise BadRequestError(
            "SVG logos are not supported. Please upload a PNG, JPEG, or WebP image."
        )
    safe_ext = "png" if ext in ("png", "jpg", "jpeg", "webp") else "png"
    key = f"logos/{pack_id}/{u.uuid4().hex}.{safe_ext}"
    uploaded_key = storage_upload_file(key, content, content_type=file.content_type)
    if not uploaded_key:
        from app.core.errors import AppError
        raise AppError("Storage not configured; cannot upload logo", status_code=503)
    logo_url = get_asset_url(key, expires_in=86400 * 7)
    if not logo_url:
        logo_url = f"key:{key}"
    pack = merge_onboarding_answers(
        db,
        pack,
        {"wordmark_svg_or_url": logo_url},
        commit=False,
    )
    pack = append_suggested_logo(db, pack, logo_url, commit=False)
    db.commit()
    return UploadLogoResponse(logo_url=logo_url)


@router.post("/{pack_id}/onboarding/generate-logo", response_model=GenerateLogoResponse)
def generate_logo_route(
    pack_id: UUID,
    body: GenerateLogoBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a logo image with the configured provider and append it to suggested_logos."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    color_palette = body.color_palette
    if not isinstance(color_palette, dict) or not color_palette:
        color_palette = extract_palette_from_answers(pack.onboarding_answers or {})
    result = generate_logo(
        brand_name=body.brand_name,
        prompt=body.prompt,
        pack_id=str(pack_id),
        color_scheme=body.color_scheme,
        brand_os_summary=body.brand_os_summary,
        color_palette=color_palette,
    )
    logo_url = result.get("logo_url") or get_logo_primary_asset_url(result) or ""
    pack = append_suggested_logos(
        db,
        pack,
        get_logo_variant_urls(result),
        commit=False,
    )
    pack = merge_onboarding_answers(
        db,
        pack,
        {
            "generated_logo_url": result.get("logo_url"),
            "transparent_logo_url": result.get("transparent_logo_url"),
        },
        commit=False,
    )
    db.commit()
    return GenerateLogoResponse(
        logo_url=logo_url,
        wordmark_svg_or_url=result.get("wordmark_svg_or_url"),
        transparent_logo_url=result.get("transparent_logo_url"),
    )
@router.post(
    "/{pack_id}/brand-identity/suggest-typography",
    response_model=SuggestTypographyResponse,
)
def suggest_typography_route(
    pack_id: UUID,
    body: SuggestTypographyBody | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest headline and body fonts for the pack using AI. Pass current values to refine."""
    if get_pack_for_user(db, pack_id, current_user.id) is None:
        raise NotFoundError("Pack not found")
    data = suggest_typography(
        db,
        pack_id,
        current_headline=body.current_headline if body else None,
        current_body=body.current_body if body else None,
    )
    return SuggestTypographyResponse(**data)


@router.post(
    "/{pack_id}/brand-identity/suggest-palette",
    response_model=SuggestPaletteResponse,
)
def suggest_palette_route(
    pack_id: UUID,
    body: SuggestPaletteBody | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest primary/secondary/accent palette for the pack using AI. Pass current_palette to refine."""
    if get_pack_for_user(db, pack_id, current_user.id) is None:
        raise NotFoundError("Pack not found")
    data = suggest_palette(
        db,
        pack_id,
        current_palette=body.current_palette if body else None,
    )
    return SuggestPaletteResponse(**data)
