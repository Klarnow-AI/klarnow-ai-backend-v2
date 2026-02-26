"""Packs API routes."""

import json
import threading
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import SessionLocal, get_db
from app.core.errors import BadRequestError, NotFoundError
from app.modules.packs.models import Pack, User
from app.core.storage import upload_file as storage_upload_file, get_presigned_url
from app.modules.packs.schemas import (
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
    ConversionPageSummary,
    PlanTrackerSummary,
    LeadsSummary,
    ProposalsSummary,
    InvoicesSummary,
    OnboardingSubmit,
    OnboardingCompleteResponse,
    OnboardingCompleteAccepted,
    ExtractBrandBody,
    ExtractBrandResponse,
    GenerateStarterBrandBody,
    GenerateStarterBrandResponse,
    GenerateLogoBody,
    GenerateLogoResponse,
    UploadLogoResponse,
    GenerateMockupsResponse,
    MockupItemResponse,
    SuggestTypographyBody,
    SuggestTypographyResponse,
    SuggestPaletteBody,
    SuggestPaletteResponse,
)
from app.modules.packs.services import (
    archive_pack,
    append_suggested_logo,
    complete_onboarding,
    create_pack,
    delete_pack,
    get_pack_for_user,
    list_packs_for_user,
    merge_onboarding_answers,
    restore_pack,
    submit_onboarding,
)
from app.modules.packs.onboarding_services import extract_brand, generate_starter_brand
from app.modules.packs.logo_generation import generate_logo_with_gemini
from app.modules.packs.mockup_generation import generate_mockups
from app.modules.packs.brand_identity_suggestions import suggest_typography, suggest_palette
from app.modules.brand_os.services import get_active_for_pack, get_context_strings

router = APIRouter()


def _brand_os_summary_for_mockups(db: Session, pack_id: UUID) -> str | None:
    """Build a short summary string from the pack's active Brand OS for mockup prompts."""
    brand_os = get_active_for_pack(db, pack_id)
    if not brand_os or not brand_os.brand_strategy or not isinstance(brand_os.brand_strategy, dict):
        return None
    bs = brand_os.brand_strategy
    mission, vision, values_str, voice_str = get_context_strings(brand_os)
    pos = bs.get("positioning_differentiation") or {}
    positioning = (pos.get("statement") or "") or (pos.get("unique_advantage") or "")
    msg = bs.get("core_messaging_hierarchy") or {}
    elevator = msg.get("elevator_pitch") or ""
    parts = []
    if mission:
        parts.append(f"Mission: {mission[:200]}")
    if vision:
        parts.append(f"Vision: {vision[:200]}")
    if positioning:
        parts.append(f"Positioning: {positioning[:200]}")
    if values_str:
        parts.append(f"Values: {values_str[:150]}")
    if voice_str:
        parts.append(voice_str[:150])
    if elevator:
        parts.append(f"Elevator pitch: {elevator[:200]}")
    return " ".join(parts).strip() or None


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
        active_rows = (
            db.query(Campaign.pack_id)
            .filter(
                Campaign.pack_id.in_(pack_ids),
                Campaign.is_active.is_(True),
            )
            .all()
        )
        active_pack_ids = {r[0] for r in active_rows}
        any_rows = (
            db.query(Campaign.pack_id)
            .filter(Campaign.pack_id.in_(pack_ids))
            .distinct()
            .all()
        )
        packs_with_campaign = {r[0] for r in any_rows}
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

    from app.modules.brand_os.services import get_active_for_pack as get_brand_os, get_summary_fields
    from app.modules.campaign.services import get_active_for_pack as get_campaign
    from app.modules.conversion_page.services import get_published as get_published_page
    from app.modules.sprint.services import get_active_sprint_for_pack
    from app.modules.clients.services import list_leads_for_pack, count_qualified_leads_for_pack
    from app.modules.revenue.services import list_proposals_for_pack, list_invoices_for_pack
    from app.modules.proof_vault.services import count_for_pack as count_proofs
    from sqlalchemy import func
    from app.modules.creative.models import Asset

    brand_os = get_brand_os(db, pack_id)
    mission, vision, has_positioning = (
        get_summary_fields(brand_os) if brand_os else (None, None, False)
    )
    campaign = get_campaign(db, pack_id)
    published_page = get_published_page(db, pack_id)
    active_sprint = get_active_sprint_for_pack(db, pack_id)
    leads_list = list_leads_for_pack(db, pack_id)
    qualified_count = count_qualified_leads_for_pack(db, pack_id)
    proposals = list_proposals_for_pack(db, pack_id)
    invoices = list_invoices_for_pack(db, pack_id)
    proofs_count = count_proofs(db, pack_id)
    assets_count = db.query(func.count(Asset.id)).filter(Asset.pack_id == pack_id).scalar() or 0

    goal_summary = None
    if campaign and campaign.goal:
        g = campaign.goal if isinstance(campaign.goal, dict) else {}
        goal_summary = (g.get("description") or g.get("title") or str(g))[:200]

    # Plan & Tracker = 14-day sprint (MVP)
    sprint_day = active_sprint.current_day if active_sprint else None
    has_sprint = active_sprint is not None

    return PackSummaryResponse(
        pack=PackRead.model_validate(pack),
        brand_os=BrandOSSummary(
            mission=mission,
            vision=vision,
            has_positioning=has_positioning,
        ) if brand_os else None,
        campaign=CampaignSummary(
            primary_cta=campaign.primary_cta if campaign else None,
            goal_summary=goal_summary,
        ) if campaign else None,
        conversion_page=ConversionPageSummary(
            live_url=published_page.live_url if published_page else None,
            published_at=published_page.published_at.isoformat() if published_page and published_page.published_at else None,
        ) if published_page else None,
        plan_tracker=PlanTrackerSummary(
            horizon="14" if has_sprint else None,
            sprint_day=sprint_day,
            has_sprint=has_sprint,
        ) if has_sprint else None,
        leads=LeadsSummary(total=len(leads_list), qualified=qualified_count),
        proposals=ProposalsSummary(
            total=len(proposals),
            sent=sum(1 for p in proposals if p.status == "sent"),
            accepted=sum(1 for p in proposals if p.status == "accepted"),
            declined=sum(1 for p in proposals if p.status == "declined"),
        ),
        invoices=InvoicesSummary(
            total=len(invoices),
            sent=sum(1 for i in invoices if i.status == "sent"),
            paid=sum(1 for i in invoices if i.status == "paid"),
            overdue=sum(1 for i in invoices if i.status == "overdue"),
        ),
        proofs_count=proofs_count,
        assets_count=assets_count,
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
        can_generate_conversion_page,
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
        "website": _try_gate(can_generate_conversion_page, db, pack),
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
    # auto-create an active Campaign so downstream gates (conversion page) can proceed.
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
        pack = merge_onboarding_answers(db, pack, data["onboarding_answers"])
    
    # Day 0 completion check
    was_day_0_incomplete = pack.day_0_completed_at is None
    if was_day_0_incomplete:
        bn = (pack.brand_name or "").strip()
        cta = (pack.primary_cta or "").strip()
        usp = (pack.usp_statement or "").strip()
        if bn and cta and usp:
            pack.day_0_completed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(pack)
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
    """Run brand generation, orchestrator, and optional logo in a background thread. Sets onboarding_background_completed_at when done."""
    from app.core.logging import get_logger
    from app.modules.agents.orchestrator import handle_onboarding_complete
    from app.modules.brand_os.services import get_active_for_pack, get_summary_fields
    from app.modules.packs.models import utc_now

    logger = get_logger("klarnow.routes.packs")
    db = SessionLocal()
    try:
        pack = db.get(Pack, pack_id)
        if not pack:
            return
        answers = pack.onboarding_answers or {}
        is_existing_brand = answers.get("has_existing_brand") == "yes"
        new_brand_palette = None
        if not is_existing_brand:
            brand_name = (answers.get("brand_name") or "").strip()
            if not brand_name and answers.get("extracted_brand"):
                try:
                    extracted = json.loads(answers["extracted_brand"])
                    if isinstance(extracted, dict):
                        brand_name = (extracted.get("brand_name") or "").strip()
                except (json.JSONDecodeError, TypeError):
                    pass
            if not brand_name and (pack.brand_name or "").strip():
                brand_name = (pack.brand_name or "").strip()
            if not brand_name and pack.name:
                brand_name = (pack.name or "").strip()
            if not brand_name:
                brand_name = (pack.brand_name or pack.name or "My Brand") or "My Brand"
            raw_vibe = answers.get("vibe_chips")
            if isinstance(raw_vibe, str):
                try:
                    vibe_chips = json.loads(raw_vibe) if raw_vibe else []
                except (json.JSONDecodeError, TypeError):
                    vibe_chips = ["professional", "modern"]
            else:
                vibe_chips = raw_vibe if isinstance(raw_vibe, list) else ["professional", "modern"]
            onboarding_context = {}
            if (pack.offer_one_liner or "").strip():
                onboarding_context["offer"] = (pack.offer_one_liner or "").strip()
            if (pack.usp_statement or "").strip():
                onboarding_context["usp"] = (pack.usp_statement or "").strip()
            if (pack.target_audience or "").strip():
                onboarding_context["audience"] = (pack.target_audience or "").strip()
            if (pack.primary_cta or "").strip():
                onboarding_context["cta"] = (pack.primary_cta or "").strip()
            if answers.get("extracted_brand"):
                try:
                    ext = json.loads(answers["extracted_brand"])
                    if isinstance(ext, dict) and (ext.get("industry") or "").strip():
                        onboarding_context["industry"] = (ext.get("industry") or "").strip()
                except (json.JSONDecodeError, TypeError):
                    pass
            result = generate_starter_brand(
                brand_name, vibe_chips, onboarding_context or None, pack_id=str(pack_id),
            )
            new_brand_palette = result.get("palette")
            wordmark_to_use = result["wordmark_svg_or_url"]
            pack = append_suggested_logo(db, pack, wordmark_to_use)
            pack = merge_onboarding_answers(
                db,
                pack,
                {
                    "wordmark_svg_or_url": wordmark_to_use,
                    "palette": result["palette"],
                },
            )
            db.refresh(pack)

        handle_onboarding_complete(pack_id, db)
        db.refresh(pack)
        brand_os = get_active_for_pack(db, pack_id)
        if brand_os:
            mission, _, _ = get_summary_fields(brand_os)
            if mission:
                pack.core_concept = (mission.strip() or "")[:500]
            db.commit()
            db.refresh(pack)

        if not is_existing_brand and brand_os and new_brand_palette:
            mission, vision, _ = get_summary_fields(brand_os)
            foundation = brand_os.foundation if isinstance(brand_os.foundation, dict) else {}
            one_line = (foundation.get("one_line_offer") or "").strip()
            industry = (foundation.get("brand_industry") or "").strip()
            audience = (foundation.get("main_audience") or "").strip()
            summary_parts = [p for p in [mission, vision, one_line, industry, audience] if p]
            brand_os_summary = " ".join(summary_parts)[:1500] if summary_parts else None
            try:
                logo_result = generate_logo_with_gemini(
                    brand_name=(pack.brand_name or pack.name or "My Brand"),
                    prompt="distinctive, creative logo—professional and memorable, not generic",
                    pack_id=str(pack_id),
                    color_scheme="use the provided palette",
                    brand_os_summary=brand_os_summary,
                    color_palette=new_brand_palette,
                )
                logo_url = logo_result.get("logo_url") or logo_result.get("wordmark_svg_or_url")
                if logo_url:
                    pack = append_suggested_logo(db, pack, logo_url)
                    pack = merge_onboarding_answers(db, pack, {"wordmark_svg_or_url": logo_url})
                    db.commit()
                    db.refresh(pack)
            except Exception as e:
                logger.warning("Auto logo generation for new brand failed: %s", e, exc_info=True)

        pack = db.get(Pack, pack_id)
        if pack:
            pack.onboarding_background_completed_at = utc_now()
            db.commit()
    except Exception as e:
        logger.exception("Onboarding background task failed for pack %s: %s", pack_id, e)
    finally:
        db.close()


@router.post(
    "/{pack_id}/onboarding/complete",
    response_model=OnboardingCompleteResponse,
    responses={202: {"model": OnboardingCompleteAccepted, "description": "Processing in background; poll GET pack until onboarding_background_completed_at is set."}},
)
def complete_onboarding_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark onboarding complete and trigger Orchestrator to generate Brand OS (in background).
    Returns 202 immediately; long-running work runs in background. Poll GET pack until onboarding_background_completed_at is set."""
    from app.core.errors import AppError
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    answers = pack.onboarding_answers or {}
    if "has_existing_brand" not in answers:
        raise AppError(
            "Please complete the brand step and indicate whether you have an existing brand (yes/no).",
            status_code=400,
        )
    pack = complete_onboarding(db, pack, answers=answers)
    db.commit()
    db.refresh(pack)
    thread = threading.Thread(
        target=_run_onboarding_background,
        args=(pack_id,),
        daemon=True,
    )
    thread.start()
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "processing", "pack_id": str(pack_id)},
    )


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
    pack = append_suggested_logo(db, pack, wordmark)
    pack = merge_onboarding_answers(
        db,
        pack,
        {
            "wordmark_svg_or_url": wordmark,
            "palette": result["palette"],
        },
    )
    return GenerateStarterBrandResponse(
        wordmark_svg_or_url=wordmark,
        palette=result["palette"],
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
    logo_url = get_presigned_url(key, expires_in=86400 * 7)
    if not logo_url:
        logo_url = f"key:{key}"
    current = dict(pack.onboarding_answers or {})
    current["wordmark_svg_or_url"] = logo_url
    pack = merge_onboarding_answers(db, pack, current)
    pack = append_suggested_logo(db, pack, logo_url)
    return UploadLogoResponse(logo_url=logo_url)


@router.post("/{pack_id}/onboarding/generate-logo", response_model=GenerateLogoResponse)
def generate_logo_route(
    pack_id: UUID,
    body: GenerateLogoBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a logo image with Gemini; append to suggested_logos and optionally set as wordmark."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    result = generate_logo_with_gemini(
        brand_name=body.brand_name,
        prompt=body.prompt,
        pack_id=str(pack_id),
        color_scheme=body.color_scheme,
        brand_os_summary=body.brand_os_summary,
        color_palette=body.color_palette,
    )
    logo_url = result.get("logo_url") or result.get("wordmark_svg_or_url") or ""
    pack = append_suggested_logo(db, pack, logo_url)
    return GenerateLogoResponse(
        logo_url=logo_url,
        wordmark_svg_or_url=result.get("wordmark_svg_or_url"),
    )


def _is_raster_logo_url(url: str) -> bool:
    """Return True if the URL looks like it points to a raster image (PNG/JPEG/WebP)."""
    lower = url.lower()
    if lower.startswith("<") or lower.startswith("data:image/svg"):
        return False
    if lower.endswith(".svg"):
        return False
    path_part = lower.split("?")[0]
    if path_part.endswith(".svg"):
        return False
    return True


@router.post("/{pack_id}/brand-showcase/generate-mockups", response_model=GenerateMockupsResponse)
def generate_mockups_route(
    pack_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate brand mockup images using the pack's actual logo as reference."""
    pack = get_pack_for_user(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")

    answers = pack.onboarding_answers or {}
    logo_url = answers.get("wordmark_svg_or_url") or answers.get("wordmark_result")
    if not logo_url or not str(logo_url).strip():
        raise BadRequestError(
            "Add a logo first. We need your logo to generate brand mockups with AI."
        )
    logo_str = str(logo_url).strip()
    if not _is_raster_logo_url(logo_str):
        raise BadRequestError(
            "Mockup generation requires a PNG, JPEG, or WebP logo image. "
            "Please upload or generate a raster logo first."
        )

    brand_name = answers.get("brand_name") or getattr(pack, "brand_name", None) or "Brand"
    brand_os_summary = _brand_os_summary_for_mockups(db, pack_id)
    items = generate_mockups(
        pack_id=str(pack_id),
        brand_name=brand_name,
        logo_url=logo_str,
        brand_os_summary=brand_os_summary,
    )
    return GenerateMockupsResponse(
        items=[MockupItemResponse(**item) for item in items]
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
