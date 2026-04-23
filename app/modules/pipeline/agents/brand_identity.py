"""BrandIdentityAgent — merged visual identity + design tokens.

Replaces the old two-stage split (``identity`` → ``design_system``). Given
an approved strategy, this agent emits a single visual artifact: colors,
typography, CTA / surface treatments, plus lightweight textual fields
(``brand_archetype``, ``visual_direction``, ``logo_direction``) that exist
only to feed downstream generation.

Voice / taglines / tone live on :class:`Strategy` — they power the website
and creative agents but aren't a visual deliverable and don't belong here.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core.logging import get_logger
from app.modules.packs.logo_generation import generate_logo
from app.modules.projects.models import Project
from app.schemas.brand_identity import BrandIdentity
from app.schemas.enums import ArtifactType
from app.modules.pipeline.model_gateway import generate_structured

logger = get_logger("klarnow.pipeline.brand_identity")

SYSTEM_PROMPT = """You are a brand designer. Given an approved brand strategy,
produce a complete visual identity in one pass: colors, typography, CTA and
surface treatments, plus short textual direction that downstream agents
(website builder, creative asset generator, logo image generator) will use.

The output must be directly implementable. Use real hex values, real Google
Font names, and concrete CSS-ready values. Do NOT invent voice rules,
taglines, or personality traits — those live on the strategy artifact.

Produce:
- `brand_archetype` — single word or short phrase (e.g. "the rebel", "the sage")
- `visual_direction` — 1-2 sentences describing the visual feel
- `imagery_style` — single descriptor: "photography" / "illustration" / "abstract" / etc.
- `icon_style` — "outlined" / "filled" / "duotone" / etc.
- `logo_direction` — 2-3 sentence brief an image generator could follow
  (subject, composition, stroke weight, standalone mark vs wordmark)
- `color_palette` — 5-7 named tokens, each with `name`, `hex`, `usage`
- `typography` — 2-3 tokens (at minimum `heading` + `body`), each with
  `role`, `font_family`, `weight`, `size_class`
- `spacing_style` — "airy" / "compact" / "balanced"
- `corner_radius` — e.g. "rounded-lg", "pill", "sharp"
- `cta_styles` — primary + secondary variants with `variant`, colors, radius
- `surface_styles` — at minimum `card`, `hero`, `section` with `name` + bg
- `component_treatments` — flat map of component name → single-sentence notes

Strict schema rules (do NOT break these):
- `typography[*]` MUST use the key `font_family` (NOT `family`, `font`,
  `typeface`) along with `role`. Example:
    {"role": "heading", "font_family": "Inter", "weight": "600", "size_class": "xl"}
- `surface_styles[*]` MUST use the key `name` — NOT `role`.
    {"name": "hero", "background": "#0F1117", "corner_radius": "0px"}
- `cta_styles[*]` MUST use the key `variant` — NOT `name` or `role`.
    {"variant": "primary", "background_color": "#00E87A", "text_color": "#0F1117"}
- `color_palette[*]` MUST have `name` and `hex`.
    {"name": "Forge Black", "hex": "#0F1117", "usage": "nav, hero backgrounds"}
- `component_treatments` MUST be a flat object where every value is a
  SINGLE STRING — not a nested object. If you have multiple notes for one
  component, join them into one sentence separated by `; `.
    "nav": "Dark background with 48px tap targets; sticky on scroll"
  NOT: {"nav": {"background": "#0F1117", "tap_targets": "48px"}}
- Output must be a raw JSON object matching the schema — no wrapping in
  `properties`, no extra keys."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
    on_progress: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    strategy = inputs.get(ArtifactType.STRATEGY, {})

    user_prompt = f"""Design a complete visual identity for this strategy:

{json.dumps(strategy, indent=2)}

Generate archetype, visual_direction, logo_direction, color_palette (real hex),
typography (Google Fonts), spacing + corner_radius, cta_styles, surface_styles,
and component_treatments. Every token must be concrete and implementable."""

    result, metadata = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=BrandIdentity,
        model_tier="creative",
        temperature=0.4,
    )

    # Publish the identity *before* we kick off logo rendering. The image
    # call takes ~5-15 s and we'd rather show the palette / typography
    # straight away so the brand page has something to render while the
    # logo is cooking. ``logo_url`` stays empty at this point — the page
    # will draw an initials placeholder until the second progress call
    # replaces it with the real URL.
    if on_progress is not None:
        await on_progress(result.model_dump(mode="json"))

    # Render the actual logo image from the direction we just generated. This
    # is the piece that flips this stage from "describe visuals" to "produce
    # visuals" — ``logo_url`` is now a real asset, not an empty string waiting
    # for a human.
    logo_url, logo_metadata = await _render_logo(project=project, identity=result)
    if logo_url:
        result.logo_url = logo_url
        if on_progress is not None:
            await on_progress(result.model_dump(mode="json"))

    merged_metadata = {**metadata, "logo_generation": logo_metadata}
    return result.model_dump(mode="json"), merged_metadata


def _palette_for_logo(identity: BrandIdentity) -> dict[str, str]:
    """Pick the 2-3 hex values the logo generator should bias towards.

    Uses usage hints (``primary``, ``secondary``, ``accent``) when available,
    and falls back to positional order so the logo still gets brand colors even
    if the LLM forgets to annotate them.
    """
    palette: dict[str, str] = {}
    remaining: list[tuple[str, str]] = []
    for token in identity.color_palette:
        hex_value = (token.hex or "").strip()
        if not hex_value:
            continue
        usage = (token.usage or "").lower()
        name = (token.name or "").lower()
        target: str | None = None
        if "primary" in usage or name == "primary":
            target = "primary"
        elif "secondary" in usage or name == "secondary":
            target = "secondary"
        elif "accent" in usage or name == "accent":
            target = "accent"
        if target and target not in palette:
            palette[target] = hex_value
        else:
            remaining.append((token.name or hex_value, hex_value))
    for slot in ("primary", "secondary", "accent"):
        if slot in palette or not remaining:
            continue
        _, hex_value = remaining.pop(0)
        palette[slot] = hex_value
    return palette


def _logo_prompt(identity: BrandIdentity) -> str:
    parts: list[str] = []
    direction = (identity.logo_direction or "").strip()
    if direction:
        parts.append(direction)
    visual = (identity.visual_direction or "").strip()
    if visual:
        parts.append(f"Overall visual feel: {visual}")
    archetype = (identity.brand_archetype or "").strip()
    if archetype:
        parts.append(f"Brand archetype: {archetype}")
    return ". ".join(parts) if parts else "simple, distinctive mark"


async def _render_logo(
    *,
    project: Project,
    identity: BrandIdentity,
) -> tuple[str, dict[str, Any]]:
    """Call the image-gen provider and return ``(logo_url, metadata)``.

    Non-strict: if generation is disabled or the provider fails we log and
    return an empty URL. The rest of the brand identity is still useful on its
    own, and a downstream "regenerate logo" action can retry.
    """
    brand_name = (project.name or "Brand").strip() or "Brand"
    prompt_text = _logo_prompt(identity)
    palette = _palette_for_logo(identity)
    namespace = str(project.id)

    def _call() -> dict[str, Any]:
        return generate_logo(
            brand_name=brand_name,
            prompt=prompt_text,
            pack_id=namespace,
            color_scheme=identity.visual_direction,
            brand_os_summary=identity.brand_archetype,
            color_palette=palette or None,
            strict=False,
        )

    try:
        result = await asyncio.to_thread(_call)
    except Exception as exc:  # pragma: no cover - defensive, generate_logo already catches most
        logger.warning(
            "brand_identity: logo generation raised unexpectedly: %s",
            exc,
            exc_info=True,
        )
        return "", {"status": "error", "error": str(exc)}

    logo_url = (result.get("logo_url") or "").strip()
    transparent_url = (result.get("transparent_logo_url") or "").strip()
    if not logo_url:
        return "", {
            "status": "skipped",
            "reason": "provider disabled or returned no image",
        }
    return logo_url, {
        "status": "ok",
        "logo_url": logo_url,
        "transparent_logo_url": transparent_url or None,
        "model": None,
    }
