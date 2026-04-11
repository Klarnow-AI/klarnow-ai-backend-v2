"""Export all brand package assets as a ZIP archive.

Produces a structured ZIP:
  /strategy/brand-strategy.txt
  /strategy/brand-identity.txt
  /logo/logo-primary.png
  /logo/logo-transparent.png
  /social/instagram-post.png
  /social/instagram-story.png
  /social/linkedin-banner.png
  /social/facebook-cover.png
  /social/twitter-header.png
  /brand-guide/brand-guide.pdf
"""
from __future__ import annotations

import io
import json
import zipfile
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.modules.packs.models import Pack

logger = get_logger("klarnow.export")


def _download_asset(url: str, timeout: int = 30) -> bytes | None:
    """Download a remote asset, return bytes or None on failure."""
    if not url or not isinstance(url, str) or url.startswith("data:"):
        return None
    try:
        resp = requests.get(url.strip(), timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning(f"Failed to download asset: {e}")
        return None


def _add_text_file(zf: zipfile.ZipFile, path: str, content: str) -> None:
    """Write a text file into the ZIP."""
    zf.writestr(path, content.encode("utf-8"))


def _add_downloaded_asset(
    zf: zipfile.ZipFile,
    path: str,
    url: str | None,
    ext: str = "png",
) -> bool:
    """Download a URL and write it to the ZIP. Returns True if successful."""
    if not url:
        return False
    data = _download_asset(url)
    if not data:
        return False
    zf.writestr(path, data)
    return True


def build_strategy_text(pack: Pack, brand_os_data: dict | None) -> str:
    """Build a human-readable strategy summary."""
    lines = []
    brand_name = pack.brand_name or pack.name or "Brand"
    lines.append(f"Brand Strategy: {brand_name}")
    lines.append("=" * 60)
    lines.append("")

    if brand_os_data:
        foundation = brand_os_data.get("foundation") or {}
        strategy = brand_os_data.get("brand_strategy") or {}

        if foundation.get("brand_name"):
            lines.append(f"Brand Name: {foundation['brand_name']}")
        if foundation.get("one_line_offer"):
            lines.append(f"One-line offer: {foundation['one_line_offer']}")
        if foundation.get("brand_purpose"):
            lines.append(f"Brand purpose: {', '.join(foundation['brand_purpose'])}")
        if foundation.get("main_audience"):
            lines.append(f"Target audience: {', '.join(foundation['main_audience'])}")

        lines.append("")

        pos = strategy.get("positioning_differentiation") or {}
        if pos.get("statement"):
            lines.append(f"Positioning: {pos['statement']}")
        if pos.get("unique_advantage"):
            lines.append(f"Unique advantage: {pos['unique_advantage']}")

        messaging = strategy.get("core_messaging_hierarchy") or {}
        if messaging.get("elevator_pitch"):
            lines.append(f"\nElevator pitch: {messaging['elevator_pitch']}")
        if messaging.get("proof_points"):
            lines.append("\nKey messages:")
            for pp in messaging["proof_points"]:
                lines.append(f"  - {pp}")

        voice = strategy.get("voice_personality") or {}
        if voice.get("archetype"):
            lines.append(f"\nBrand archetype: {voice['archetype']}")
        if voice.get("profile"):
            lines.append(f"Voice profile: {', '.join(voice['profile'])}")
        if voice.get("we_are"):
            lines.append(f"We are: {', '.join(voice['we_are'])}")
        if voice.get("we_are_not"):
            lines.append(f"We are not: {', '.join(voice['we_are_not'])}")

    return "\n".join(lines)


def build_identity_text(pack: Pack, brand_os_data: dict | None) -> str:
    """Build a human-readable identity summary."""
    lines = []
    brand_name = pack.brand_name or pack.name or "Brand"
    lines.append(f"Brand Identity: {brand_name}")
    lines.append("=" * 60)
    lines.append("")

    if brand_os_data:
        strategy = brand_os_data.get("brand_strategy") or {}
        voice = strategy.get("voice_personality") or {}
        style = strategy.get("style_direction_seeds") or {}

        if voice.get("archetype"):
            lines.append(f"Personality archetype: {voice['archetype']}")
        if voice.get("profile"):
            lines.append(f"Tone of voice: {', '.join(voice['profile'])}")
        if style.get("design_cues"):
            lines.append(f"Visual style: {'. '.join(style['design_cues'])}")
        if voice.get("we_are"):
            lines.append(f"\nDo's: {', '.join(voice['we_are'])}")
        if voice.get("we_are_not"):
            lines.append(f"Don'ts: {', '.join(voice['we_are_not'])}")

    answers = pack.onboarding_answers or {}
    if answers.get("tagline"):
        lines.append(f"\nTagline: {answers['tagline']}")

    return "\n".join(lines)


def generate_export_zip(
    *,
    db: Session,
    pack: Pack,
    pack_id: UUID,
    brand_os_data: dict | None = None,
    brand_guide_pdf: bytes | None = None,
) -> io.BytesIO:
    """Generate a complete brand package ZIP.

    Args:
        db: Database session
        pack: The Pack model instance
        pack_id: Pack UUID
        brand_os_data: Raw Brand OS dict (foundation + brand_strategy)
        brand_guide_pdf: Pre-generated brand guide PDF bytes (optional)

    Returns:
        BytesIO buffer containing the ZIP archive
    """
    answers = pack.onboarding_answers or {}
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Strategy text
        strategy_text = build_strategy_text(pack, brand_os_data)
        _add_text_file(zf, "strategy/brand-strategy.txt", strategy_text)

        # 2. Identity text
        identity_text = build_identity_text(pack, brand_os_data)
        _add_text_file(zf, "strategy/brand-identity.txt", identity_text)

        # 3. Logo assets
        logo_url = answers.get("generated_logo_url")
        transparent_url = answers.get("transparent_logo_url")
        _add_downloaded_asset(zf, "logo/logo-primary.png", logo_url)
        _add_downloaded_asset(zf, "logo/logo-transparent.png", transparent_url)

        suggested = answers.get("suggested_logos") or []
        for i, surl in enumerate(suggested):
            if isinstance(surl, str) and surl.strip():
                _add_downloaded_asset(zf, f"logo/variation-{i + 1}.png", surl)

        # 4. Social media assets
        social_data = answers.get("social_assets") or {}
        for platform_key in [
            "instagram_post",
            "instagram_story",
            "linkedin_banner",
            "facebook_cover",
            "twitter_header",
        ]:
            entry = social_data.get(platform_key)
            if isinstance(entry, dict) and entry.get("url"):
                _add_downloaded_asset(
                    zf,
                    f"social/{platform_key.replace('_', '-')}.png",
                    entry["url"],
                )

        # 5. Brand guide PDF
        if brand_guide_pdf:
            zf.writestr("brand-guide/brand-guide.pdf", brand_guide_pdf)

        # 6. Raw data export (JSON)
        raw_data = {
            "brand_name": pack.brand_name,
            "core_concept": pack.core_concept,
            "primary_cta": pack.primary_cta,
            "target_audience": pack.target_audience,
        }
        if brand_os_data:
            raw_data["brand_os"] = brand_os_data
        _add_text_file(zf, "data/brand-data.json", json.dumps(raw_data, indent=2, default=str))

    buf.seek(0)
    return buf
