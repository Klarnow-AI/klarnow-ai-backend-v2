"""Packs API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
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
    PackGatesResponse,
    GateStatus,
    SectionUnlock,
    BrandOSSummary,
    CampaignSummary,
    WebsiteSummary,
    PlanTrackerSummary,
    LeadsSummary,
    ProposalsSummary,
    InvoicesSummary,
    OnboardingSubmit,
    OnboardingCompleteResponse,
    OnboardingJobStatusResponse,
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
from app.modules.packs.onboarding_jobs import (
    get_onboarding_job_status,
)
from app.modules.sprint.day_readiness import get_day_readiness_state, is_day_ready_to_complete

router = APIRouter()


@router.get("", response_model=PackList)
def list_my_packs(
    include_archived: bool = Query(False, description="Include archived packs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List packs for the authenticated user with campaign status."""
    from app.modules.campaign.models import Campaign

    packs = list_packs_for_user(db, current_user.id, include_archived=include_archived)
    pack_ids = [p.id for p in packs]
    active_pack_ids = set()
    packs_with_campaign = set()
    if pack_ids:
        campaign_rows = (
            db.query(Campaign.pack_id, func.bool_or(Campaign.is_active).label("has_active"))
            .filter(Campaign.pack_id.in_(pack_ids))
            .group_by(Campaign.pack_id)
            .all()
        )
        active_pack_ids = {r.pack_id for r in campaign_rows if r.has_active}
        packs_with_campaign = {r.pack_id for r in campaign_rows}
    items = []
    for p in packs:
        data = PackRead.model_validate(p).model_dump()
        campaign_is_active: bool | None
        if p.id not in packs_with_campaign:
            campaign_is_active = None
        else:
            campaign_is_active = p.id in active_pack_ids
        items.append(PackListItem(**data, campaign_is_active=campaign_is_active))
    return PackList(items=items, total=len(packs))


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
    """Get full pack overview: Brand OS through Proof Vault (for overview page)."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    from app.modules.brand_os.models import BrandOS
    from app.modules.campaign.models import Campaign as CampaignModel
    from app.modules.builder.models import BuilderProject
    from app.modules.sprint.models import Sprint, SPRINT_STATUS_ACTIVE
    from app.modules.clients.models import LEAD_STATUS_QUALIFIED, Lead
    from app.modules.docs.models import Document
    from app.modules.proof_vault.models import Proof
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
            select(CampaignModel.id)
                .where(CampaignModel.pack_id == pack_id, CampaignModel.is_active.is_(True))
                .limit(1)
                .scalar_subquery()
                .label("campaign_id"),
            select(CampaignModel.goal)
                .where(CampaignModel.pack_id == pack_id, CampaignModel.is_active.is_(True))
                .limit(1)
                .scalar_subquery()
                .label("campaign_goal"),
            select(CampaignModel.primary_cta)
                .where(CampaignModel.pack_id == pack_id, CampaignModel.is_active.is_(True))
                .limit(1)
                .scalar_subquery()
                .label("campaign_cta"),
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
            select(Sprint.current_day)
                .where(Sprint.pack_id == pack_id, Sprint.status == SPRINT_STATUS_ACTIVE)
                .order_by(Sprint.started_at.desc())
                .limit(1)
                .scalar_subquery()
                .label("sprint_day"),
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

    has_campaign = meta["campaign_id"] is not None
    has_site = meta["site_live_url"] is not None
    sprint_day = meta["sprint_day"]
    has_sprint = sprint_day is not None
    counts = (
        db.execute(
            select(
                select(func.count(Lead.id))
                .where(Lead.pack_id == pack_id)
                .scalar_subquery()
                .label("leads_total"),
                select(func.count(Lead.id))
                .where(
                    Lead.pack_id == pack_id,
                    Lead.status == LEAD_STATUS_QUALIFIED,
                )
                .scalar_subquery()
                .label("leads_qualified"),
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
                select(func.count(Proof.id))
                .where(Proof.pack_id == pack_id)
                .scalar_subquery()
                .label("proofs_count"),
                select(func.count(Asset.id))
                .where(Asset.pack_id == pack_id)
                .scalar_subquery()
                .label("assets_count"),
            )
        )
        .one()
        ._mapping
    )

    goal_summary = None
    if has_campaign and meta["campaign_goal"]:
        g = meta["campaign_goal"] if isinstance(meta["campaign_goal"], dict) else {}
        goal_summary = (g.get("description") or g.get("title") or str(g))[:200]

    # Plan & Tracker = 14-day sprint (MVP)

    return PackSummaryResponse(
        pack=PackRead.model_validate(pack),
        brand_os=BrandOSSummary(
            mission=mission,
            vision=vision,
            has_positioning=has_positioning,
        ) if has_brand_os else None,
        campaign=CampaignSummary(
            primary_cta=meta["campaign_cta"],
            goal_summary=goal_summary,
        ) if has_campaign else None,
        website=WebsiteSummary(
            live_url=meta["site_live_url"],
            published_at=meta["site_published_at"].isoformat() if meta["site_published_at"] else None,
        ) if has_site else None,
        plan_tracker=PlanTrackerSummary(
            horizon="14" if has_sprint else None,
            sprint_day=sprint_day,
            has_sprint=has_sprint,
        ) if has_sprint else None,
        leads=LeadsSummary(
            total=int(counts["leads_total"] or 0),
            qualified=int(counts["leads_qualified"] or 0),
        ),
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
        proofs_count=int(counts["proofs_count"] or 0),
        assets_count=int(counts["assets_count"] or 0),
    )


@router.get("/{pack_id}/gates", response_model=PackGatesResponse)
def get_pack_gates(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Evaluate all gates for a pack and return section unlock status."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    from app.core.errors import GateBlockedError
    from app.core.gates import (
        can_generate_website,
        can_generate_assets,
        can_create_proposal,
        can_create_invoice,
        can_pass_pack_gate,
        can_pass_paywall_gate,
        can_pass_day7_gate,
        can_pass_day8_gate,
    )
    from app.modules.sprint.services import get_active_sprint_for_pack

    active_sprint = get_active_sprint_for_pack(db, pack_id)
    current_day = active_sprint.current_day if active_sprint else None

    pack_ok, pack_msg = can_pass_pack_gate(pack)
    paywall_ok, paywall_msg = can_pass_paywall_gate(db, current_user.id, current_day or 0)
    d7_ok, d7_msg = can_pass_day7_gate(db, pack)
    d8_ok, d8_msg = can_pass_day8_gate(db, pack)

    def _try_gate(fn, *args) -> SectionUnlock:
        try:
            fn(*args)
            return SectionUnlock(unlocked=True)
        except GateBlockedError as e:
            return SectionUnlock(unlocked=False, reason=str(e))

    sections: dict[str, SectionUnlock] = {
        "brand_os": SectionUnlock(unlocked=True),
        "website": _try_gate(can_generate_website, db, pack),
        "posters": _try_gate(can_generate_assets, db, pack),
        "ad_factory": _try_gate(can_generate_assets, db, pack),
        "leads": SectionUnlock(unlocked=True),
        "proposal": _try_gate(can_create_proposal, db, pack),
        "invoice": _try_gate(can_create_invoice, db, pack),
        "proof_vault": SectionUnlock(unlocked=True),
    }

    return PackGatesResponse(
        pack_gate=GateStatus(passed=pack_ok, message=pack_msg or None),
        paywall_gate=GateStatus(passed=paywall_ok, message=paywall_msg or None),
        day7_gate=GateStatus(passed=d7_ok, message=d7_msg or None),
        day8_gate=GateStatus(passed=d8_ok, message=d8_msg or None),
        current_day=current_day,
        has_sprint=active_sprint is not None,
        sections=sections,
    )


@router.get("/{pack_id}/day-readiness", response_model=DayReadinessResponse)
def get_day_readiness(
    pack_id: UUID,
    day: int = Query(..., ge=0, le=3, description="Day number (0-3)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return whether all required questions for the given day (0-3) have been answered."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    from app.modules.sprint.day_readiness import is_day_ready_to_complete

    ready = is_day_ready_to_complete(db, pack_id, day)
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
    """Update pack (name, client_id, Day 0 fields). Sets day_0_completed_at when brand_name + primary_cta + usp_statement are all set."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    from app.modules.clients.services import get_for_user as get_client_for_user
    from datetime import datetime, timezone
    data = body.model_dump(exclude_unset=True)
    if "client_id" in data:
        cid = data["client_id"]
        if cid is not None and get_client_for_user(db, cid, current_user.id) is None:
            raise NotFoundError("Client not found")
        pack.client_id = cid
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

    # Convenience: if Day 0 sets pack.primary_cta but no active Campaign exists yet,
    # auto-create an active Campaign so downstream gates (website) can proceed.
    if "primary_cta" in data:
        cta = (pack.primary_cta or "").strip()
        if cta:
            from app.modules.campaign.services import get_active_for_pack as get_active_campaign
            active_campaign = get_active_campaign(db, pack_id)
            if active_campaign:
                if not pack.active_campaign_id:
                    pack.active_campaign_id = active_campaign.id
            else:
                if not pack.active_campaign_id:
                    from app.core.governance import validate_one_cta
                    from app.modules.campaign.models import Campaign

                    validate_one_cta(cta)
                    campaign = Campaign(
                        pack_id=pack_id,
                        version="A",
                        primary_cta=cta,
                        goal=None,
                        angles=[],
                        is_active=True,
                    )
                    db.add(campaign)
                    db.flush()
                    pack.active_campaign_id = campaign.id
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
    answers = pack.onboarding_answers or {}
    if answers.get("has_existing_brand") not in {"yes", "no"}:
        raise BadRequestError(
            "Please complete Step 0 and indicate whether this is an existing brand."
        )
    for day in (0, 1, 2):
        readiness = get_day_readiness_state(db, pack.id, day)
        if readiness.get("ready"):
            continue
        message = readiness.get("reason") or f"Step {day} is not ready to complete."
        raise BadRequestError(message)


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
    response_model=OnboardingCompleteResponse,
)
def complete_onboarding_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize onboarding after Step 2 and generate Brand OS synchronously."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    _require_step_2_finalization_ready(db, pack)

    sync_pack_target_audience(pack)
    finalization_payload = build_step_2_finalization_payload(pack)
    fingerprint = fingerprint_payload(finalization_payload)
    answers = pack.onboarding_answers or {}
    is_existing_brand = answers.get("has_existing_brand") == "yes"

    cached = get_step_2_finalization_cache(pack) or {}
    if cached.get("fingerprint") != fingerprint:
        cached = {"fingerprint": fingerprint}

    brand_os_row = None
    cached_brand_os_id = cached.get("brand_os_id")
    if isinstance(cached_brand_os_id, str):
        try:
            brand_os_row = get_brand_os_by_id_and_pack(db, UUID(cached_brand_os_id), pack_id)
        except ValueError:
            brand_os_row = None
    if brand_os_row is None:
        brand_os_row = get_brand_os_by_source_job_id(db, pack_id, fingerprint)
    if brand_os_row is None:
        generated_brand_os = generate_brand_os(
            db,
            pack_id,
            source_job_id=fingerprint,
            allow_without_onboarding_complete=True,
        )
        generated_brand_os_id = _resolve_brand_os_id(generated_brand_os)
        if generated_brand_os_id is not None:
            brand_os_row = get_brand_os_by_id_and_pack(db, generated_brand_os_id, pack_id)
        if brand_os_row is None:
            brand_os_row = get_brand_os_by_source_job_id(db, pack_id, fingerprint)
    if brand_os_row is None:
        raise BadRequestError("Brand OS generation failed. Please retry.")

    cached["brand_os_id"] = str(brand_os_row.id)
    cached["brand_os_version"] = brand_os_row.version
    set_step_2_finalization_cache(pack, cached)
    db.commit()
    db.refresh(pack)

    starter_brand_response: GenerateStarterBrandResponse | None = None
    logo_response: GenerateLogoResponse | None = None

    if not is_existing_brand:
        cached_starter_brand = cached.get("starter_brand")
        if isinstance(cached_starter_brand, dict):
            try:
                starter_brand_response = GenerateStarterBrandResponse.model_validate(cached_starter_brand)
            except Exception:
                starter_brand_response = None
        if starter_brand_response is None:
            starter_brand_result = generate_starter_brand(
                brand_name=(pack.brand_name or pack.name or "My Brand"),
                vibe_chips=resolve_pack_vibe_chips(pack),
                onboarding_context=build_onboarding_context(pack),
                pack_id=str(pack_id),
            )
            wordmark = starter_brand_result["wordmark_svg_or_url"]
            pack = append_suggested_logos(
                db,
                pack,
                get_logo_variant_urls(starter_brand_result) or [wordmark],
                commit=False,
            )
            pack = merge_onboarding_answers(
                db,
                pack,
                {
                    "wordmark_svg_or_url": wordmark,
                    "generated_logo_url": starter_brand_result.get("logo_url"),
                    "transparent_logo_url": starter_brand_result.get("transparent_logo_url"),
                    "palette": starter_brand_result["palette"],
                },
                commit=False,
            )
            starter_brand_response = GenerateStarterBrandResponse(
                wordmark_svg_or_url=wordmark,
                palette=starter_brand_result["palette"],
                logo_url=starter_brand_result.get("logo_url"),
                transparent_logo_url=starter_brand_result.get("transparent_logo_url"),
            )
            cached["starter_brand"] = starter_brand_response.model_dump()
            set_step_2_finalization_cache(pack, cached)
            db.commit()
            db.refresh(pack)

        cached_logo = cached.get("logo")
        if isinstance(cached_logo, dict):
            try:
                logo_response = GenerateLogoResponse.model_validate(cached_logo)
            except Exception:
                logo_response = None
        if logo_response is None:
            palette = starter_brand_response.palette if starter_brand_response else None
            if not isinstance(palette, dict) or not palette:
                palette = extract_palette_from_answers(pack.onboarding_answers or {})
            logo_result = generate_logo(
                brand_name=(pack.brand_name or pack.name or "My Brand"),
                prompt="distinctive, creative logo, professional and memorable, not generic",
                pack_id=str(pack_id),
                color_scheme="use the provided palette",
                brand_os_summary=_build_brand_os_summary_text(brand_os_row),
                color_palette=palette,
            )
            logo_url = logo_result.get("logo_url") or get_logo_primary_asset_url(logo_result) or ""
            pack = append_suggested_logos(
                db,
                pack,
                get_logo_variant_urls(logo_result),
                commit=False,
            )
            pack = merge_onboarding_answers(
                db,
                pack,
                {
                    "generated_logo_url": logo_result.get("logo_url"),
                    "transparent_logo_url": logo_result.get("transparent_logo_url"),
                },
                commit=False,
            )
            logo_response = GenerateLogoResponse(
                logo_url=logo_url,
                wordmark_svg_or_url=logo_result.get("wordmark_svg_or_url"),
                transparent_logo_url=logo_result.get("transparent_logo_url"),
            )
            cached["logo"] = logo_response.model_dump()
            set_step_2_finalization_cache(pack, cached)
            db.commit()
            db.refresh(pack)

    answers = pack.onboarding_answers or {}
    pack = complete_onboarding(db, pack, answers=answers, commit=False)
    cached["completed_at"] = (
        pack.onboarding_completed_at.isoformat() if pack.onboarding_completed_at else None
    )
    set_step_2_finalization_cache(pack, cached)
    db.commit()
    db.refresh(pack)

    return OnboardingCompleteResponse(
        pack=PackRead.model_validate(pack),
        is_existing_brand=is_existing_brand,
        brand_os=brand_os_read_from_orm(brand_os_row),
        starter_brand=starter_brand_response,
        logo=logo_response,
    )


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
