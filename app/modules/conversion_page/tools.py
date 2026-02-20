"""Conversion page tool: generate_conversion_page (Conversion Agent). React-driven structure with AI-generated visuals."""

from typing import Any
from uuid import UUID
import concurrent.futures

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.governance import validate_conversion_page_cta
from app.core.logging import get_logger
from app.modules.brand_os.services import get_active_for_pack, get_context_strings
from app.modules.campaign.services import get_active_for_pack as get_campaign_for_pack
from app.modules.conversion_page.models import ConversionPage
from app.modules.conversion_page.services import list_versions
from app.modules.conversion_page.copy_generation import generate_marketing_copy, PackContext, MarketingCopy
from app.modules.conversion_page.image_generation import get_hero_background_data
from app.modules.conversion_page.design_generation import generate_design_tokens, DesignTokens
from app.modules.packs.models import Pack

logger = get_logger("klarnow.conversion_page.tools")


GENERATE_CONVERSION_PAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
    },
    "required": ["pack_id"],
}


def _next_version(existing: list[str]) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    used = {v for v in existing if len(v) == 1 and v in letters}
    for c in letters:
        if c not in used:
            return c
    return "Z1"


def _build_pack_context(pack: Pack, brand_os) -> PackContext:
    """Build PackContext dict from Pack and Brand OS data."""
    context: PackContext = {
        "brand_name": pack.brand_name or "Your Brand",
        "offer_one_liner": pack.offer_one_liner or "",
        "target_audience": pack.target_audience or "",
        "primary_cta": pack.primary_cta or "",
        "business_type": pack.business_type or "service",
    }
    
    # Add optional Pack fields if present
    if pack.usp_locked_line:
        context["usp_locked_line"] = pack.usp_locked_line
    if pack.usp_statement:
        context["usp_statement"] = pack.usp_statement
    if pack.usp_proof:
        context["usp_proof"] = pack.usp_proof
    if pack.primary_pain:
        context["primary_pain"] = pack.primary_pain
    if pack.primary_outcome:
        context["primary_outcome"] = pack.primary_outcome
    if pack.hero_angle:
        context["hero_angle"] = pack.hero_angle
    if pack.location_city:
        context["location_city"] = pack.location_city
    if pack.location_country:
        context["location_country"] = pack.location_country
    
    # Add Brand OS context if available
    if brand_os:
        mission, _, _, voice_str = get_context_strings(brand_os)
        if mission:
            context["mission"] = mission
        if voice_str:
            context["voice_str"] = voice_str
    
    return context


def _assemble_page_structure(
    marketing_copy: MarketingCopy,
    hero_background: dict[str, Any],
    design_tokens: DesignTokens,
    primary_cta: str,
) -> dict[str, Any]:
    """
    Assemble complete page structure from generated components.
    
    Args:
        marketing_copy: Generated copy from copy_generation
        hero_background: Background data (image URL or gradient) from image_generation
        design_tokens: Design tokens from design_generation
        primary_cta: Locked CTA label
        
    Returns:
        Complete structure dict for ConversionPage model
    """
    # Build sections with generated copy
    sections = []
    
    # Hero section with background
    hero_props = marketing_copy.get("hero", {})
    if hero_background.get("type") == "image":
        hero_props["backgroundImage"] = hero_background["url"]
    else:
        hero_props["gradientFrom"] = hero_background.get("from", "#6366f1")
        hero_props["gradientTo"] = hero_background.get("to", "#4f46e5")
    sections.append({"type": "hero", "props": hero_props})
    
    # Benefits section
    benefits_props = marketing_copy.get("benefits", {})
    sections.append({"type": "benefits", "props": benefits_props})
    
    # Social proof section
    social_proof_props = marketing_copy.get("social_proof", {})
    sections.append({"type": "socialProof", "props": social_proof_props})
    
    # Lead form section
    lead_form_props = marketing_copy.get("lead_form", {})
    sections.append({"type": "leadForm", "props": lead_form_props})
    
    # CTA section with locked label
    cta_props = marketing_copy.get("cta", {})
    cta_props["label"] = primary_cta  # Enforce CTA lock
    sections.append({"type": "cta", "props": cta_props})
    
    # Assemble complete structure
    structure = {
        "sections": sections,
        "design": design_tokens,
        "seo": marketing_copy.get("seo", {
            "title": "Landing Page",
            "description": ""
        })
    }
    
    return structure


def _stub_structure(primary_cta: str) -> dict:
    return {
        "sections": [
            {"type": "hero", "props": {"headline": "Your headline", "subheadline": "Subheadline"}},
            {"type": "cta", "props": {"label": primary_cta, "action": "primary"}},
        ],
        "seo": {"title": "Landing", "description": ""},
    }


def generate_conversion_page(db: Session, pack_id: UUID | str, skip_images: bool = False) -> dict:
    """
    Create a new conversion page version with AI-generated copy, images, and design.
    
    Args:
        db: Database session
        pack_id: Pack UUID or string
        skip_images: If True, skip image generation (faster, uses gradients)
        
    Returns:
        Dict with version and conversion_page_id
        
    Raises:
        ValueError: If pack not found or required data missing (including Day 3 fields)
    """
    pack_id = UUID(str(pack_id)) if isinstance(pack_id, str) else pack_id
    pack = db.query(Pack).filter(Pack.id == pack_id).first()
    if not pack:
        raise ValueError("Pack not found")
    
    # Require Day 3 fields before generating
    if not pack.primary_pain:
        raise ValueError("Primary pain is required (Day 2)")
    if not pack.primary_outcome:
        raise ValueError("Primary outcome is required (Day 2)")
    if not pack.hero_angle:
        raise ValueError("Hero angle is required (Day 3)")
    
    from app.core.gates import can_generate_conversion_page
    can_generate_conversion_page(db, pack)
    
    campaign = get_campaign_for_pack(db, pack_id)
    if not campaign or not campaign.primary_cta:
        raise ValueError("Campaign must have a primary CTA before generating conversion page")
    
    primary_cta = campaign.primary_cta
    brand_os = get_active_for_pack(db, pack_id)
    
    logger.info(f"Generating conversion page for pack {pack_id}: {pack.brand_name or pack.name}")
    
    # Build context for generation
    pack_context = _build_pack_context(pack, brand_os)
    brand_name = pack_context.get("brand_name", "Your Brand")
    
    # Stage 1: Generate marketing copy (always required)
    logger.info("Stage 1: Generating marketing copy")
    marketing_copy = generate_marketing_copy(pack_context, primary_cta)
    
    # Stage 2 & 3: Generate images and design tokens in parallel (if not skipped)
    hero_background: dict[str, Any]
    design_tokens: DesignTokens
    
    if skip_images:
        logger.info("Image generation skipped, using gradient fallback")
        from app.modules.conversion_page.image_generation import _generate_gradient_fallback
        gradient = _generate_gradient_fallback(
            pack_context.get("hero_angle", "quality"),
            pack_context.get("business_type", "service")
        )
        hero_background = {"type": "gradient", **gradient}
        
        # Still generate design tokens
        logger.info("Stage 3: Generating design tokens")
        design_tokens = generate_design_tokens(
            brand_name=brand_name,
            business_type=pack_context.get("business_type", "service"),
            hero_angle=pack_context.get("hero_angle", "quality"),
        )
    else:
        # Run image and design generation in parallel
        logger.info("Stages 2 & 3: Generating hero image and design tokens in parallel")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            image_future = executor.submit(
                get_hero_background_data,
                pack_id=str(pack_id),
                brand_name=brand_name,
                offer=pack_context.get("offer_one_liner", ""),
                hero_angle=pack_context.get("hero_angle", "quality"),
                business_type=pack_context.get("business_type", "service"),
                target_audience=pack_context.get("target_audience"),
            )
            
            design_future = executor.submit(
                generate_design_tokens,
                brand_name=brand_name,
                business_type=pack_context.get("business_type", "service"),
                hero_angle=pack_context.get("hero_angle", "quality"),
            )
            
            # Wait for both to complete
            hero_background = image_future.result()
            design_tokens = design_future.result()
    
    # Stage 4: Assemble complete structure
    logger.info("Stage 4: Assembling page structure")
    structure = _assemble_page_structure(
        marketing_copy=marketing_copy,
        hero_background=hero_background,
        design_tokens=design_tokens,
        primary_cta=primary_cta,
    )
    
    # Validate CTA enforcement
    validate_conversion_page_cta(structure, primary_cta)
    
    # Create new version
    existing_versions = [p.version for p in list_versions(db, pack_id)]
    version = _next_version(existing_versions)
    
    page = ConversionPage(
        pack_id=pack_id,
        version=version,
        structure=structure,
        seo_metadata=structure.get("seo"),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    
    logger.info(f"Conversion page generated successfully: version {version}")
    return {"version": version, "conversion_page_id": str(page.id)}
