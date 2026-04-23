"""CreativeAssetAgent — copy then code.

Two phases in one stage:

1. **Copywriter** (LLM) — produces the campaign concept, headline, body copy,
   social captions, and per-asset copy specs.
2. **Designer** (second LLM pass) — takes each spec plus the brand identity
   and writes a self-contained React/JSX component that renders the asset,
   setting :attr:`AssetSpec.jsx_code`. No image model is called — every asset
   ships as code the frontend renders in a sandboxed iframe.

The copy IS the layout brief: we feed the copywriter's headline, body, CTA,
and layout notes directly into the designer prompt alongside the brand
palette and typography so the generated JSX is on-brand and on-message. If
design generation fails for a particular asset, the copy spec still ships —
``jsx_code`` just stays empty and the UI can offer a re-render button later.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.modules.pipeline.model_gateway import generate_structured, generate_text
from app.modules.projects.models import Project
from app.schemas.creative_campaign import AssetSpec, CreativeCampaign
from app.schemas.enums import ArtifactType

logger = get_logger("klarnow.pipeline.creative_asset")

COPY_SYSTEM_PROMPT = """You are a creative director. Given a brand strategy and brand identity
(colors, typography, CTA and surface treatments), create a launch campaign with ready-to-use assets.

Generate:
- A campaign concept that ties to the business positioning
- A campaign headline
- Poster copy (headline + body + CTA)
- Flyer copy (more detailed, includes key benefits and contact info)
- 3-5 social media captions for different platforms (Instagram, LinkedIn, Facebook)
- 2-3 email subject lines
- A promotional hook (one-liner for ads or social bios)
- Asset specifications for: poster (A3), flyer (A4/letter), social posts (1:1, 4:5, 16:9)
  Each spec should include: asset_type, format, headline, body copy, CTA text, layout notes,
  and any design token overrides. Do NOT set ``jsx_code`` — the designer phase fills that in.

All copy must be consistent with the brand voice and use the design system's visual language.
Keep copy concise and action-oriented. Headlines: 2-6 words, punchy. Every word earns its place."""


DESIGN_SYSTEM_PROMPT = """You are a senior brand designer who writes JSX.

Given a copy spec and brand identity tokens, produce a SINGLE self-contained
React functional component that renders the finished poster / flyer / social
post. The component is compiled in-browser by Babel and rendered inside a
sandboxed iframe at an exact pixel size, so your JSX must be complete and
standalone.

OUTPUT FORMAT — strict:
- Return ONLY the JSX source. No prose, no markdown fences, no explanation.
- Export ONE default function component named ``Asset`` that takes no props.
- The component must be runnable as-is after a Babel JSX transform. Assume
  ``React`` is already in scope — do not write ``import``, ``export``, or
  ``require``.
- Do NOT use TypeScript syntax (no type annotations, no ``: string``, no
  generics). Plain JS + JSX only.

STYLING — strict:
- ALL styles inline via ``style={{ ... }}``. No ``className``, no
  ``styled-components``, no CSS-in-JS libraries, no external CSS.
- Root element MUST set ``width: "100%"`` and ``height: "100%"`` and
  ``position: "relative"`` and ``overflow: "hidden"`` so the asset fills the
  iframe exactly.
- Use the EXACT hex values from the brand palette. No near-matches.
- Reference fonts by ``fontFamily: "'Font Name', sans-serif"``. The iframe
  loads Google Fonts for the families on the brand identity, so stick to
  those — do not invent families.
- Typography is the star: oversized, bold, high contrast. Body copy should be
  readable at the asset's real size.

CONTENT — strict:
- Render the copy EXACTLY as given (headline, body, CTA). Do not paraphrase,
  translate, or abbreviate.
- One CTA only. Treat it as a pill / button with generous padding and a
  contrasting color.
- No fake logos, no lorem ipsum, no placeholder images. You may draw simple
  geometric shapes (circles, lines, gradients) using ``<div>`` or inline
  ``<svg>``. Do not include ``<img src="...">`` tags — there is no image
  host.
- Leave tasteful whitespace. A brand campaign, not a cheap flyer.

Example of the ONLY acceptable output shape:

function Asset() {
  return (
    <div style={{ width: "100%", height: "100%", position: "relative", overflow: "hidden", background: "#0F1117", color: "#FFFFFF", fontFamily: "'Inter', sans-serif", padding: 64, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <h1 style={{ fontSize: 96, lineHeight: 1.02, fontWeight: 700, margin: 0 }}>Launch faster.</h1>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p style={{ fontSize: 20, maxWidth: "60%", margin: 0 }}>The operator's edge, packaged for teams that ship.</p>
        <span style={{ padding: "14px 28px", borderRadius: 999, background: "#00E87A", color: "#0F1117", fontWeight: 600 }}>Get started</span>
      </div>
    </div>
  );
}

Return ONLY the ``function Asset() { ... }`` block."""


# Exact pixel dimensions we target per asset format. The iframe on the
# frontend scales the rendered component down to fit the card while keeping
# type proportions intact, so these numbers just need to be "correct" — the
# designer writes as if the asset were being exported at these sizes.
_FORMAT_TO_DIMENSIONS: dict[str, tuple[int, int]] = {
    "1x1": (1080, 1080),
    "1:1": (1080, 1080),
    "4x5": (1080, 1350),
    "4:5": (1080, 1350),
    "9x16": (1080, 1920),
    "9:16": (1080, 1920),
    "16x9": (1920, 1080),
    "16:9": (1920, 1080),
    "3x4": (1200, 1600),
    "3:4": (1200, 1600),
    # Print formats — render at 150dpi so type stays crisp when zoomed.
    "a3": (1754, 2480),
    "a4": (1240, 1754),
    "letter": (1275, 1650),
}


class _AssetJsx(BaseModel):
    """Wrapper schema so the designer LLM produces JSON we can validate.

    We ask for JSX in ``generate_text`` rather than ``generate_structured``
    because wrapping source code in JSON mangles quotes and newlines. This
    class is here for type consistency elsewhere.
    """

    jsx_code: str = Field(default="")


def _dimensions_for(spec: AssetSpec) -> tuple[int, int]:
    key = (spec.format or "").strip().lower().replace(" ", "")
    return _FORMAT_TO_DIMENSIONS.get(key, (1080, 1080))


def _palette_hint(brand_identity: dict[str, Any]) -> str:
    palette = brand_identity.get("color_palette") or []
    parts: list[str] = []
    for token in palette[:6]:
        if not isinstance(token, dict):
            continue
        name = str(token.get("name") or "").strip()
        hex_value = str(token.get("hex") or "").strip()
        if not hex_value:
            continue
        parts.append(f"{name or 'color'} {hex_value}")
    return ", ".join(parts)


def _typography_hint(brand_identity: dict[str, Any]) -> str:
    typography = brand_identity.get("typography") or []
    parts: list[str] = []
    for token in typography[:3]:
        if not isinstance(token, dict):
            continue
        role = str(token.get("role") or "").strip() or "type"
        family = str(token.get("font_family") or "").strip()
        if not family:
            continue
        parts.append(f"{role}: {family}")
    return "; ".join(parts)


def _build_design_prompt(
    *,
    spec: AssetSpec,
    brand_identity: dict[str, Any],
    campaign_concept: str,
    width_px: int,
    height_px: int,
) -> str:
    asset_type = (spec.asset_type or "asset").replace("_", " ")
    palette = _palette_hint(brand_identity)
    typography = _typography_hint(brand_identity)
    visual_direction = (brand_identity.get("visual_direction") or "").strip()
    archetype = (brand_identity.get("brand_archetype") or "").strip()

    copy_lines: list[str] = []
    if spec.headline:
        copy_lines.append(f"HEADLINE (render exactly): {spec.headline}")
    if spec.body_copy:
        copy_lines.append(f"BODY (render exactly): {spec.body_copy}")
    if spec.cta_text:
        copy_lines.append(f"CTA button label (render exactly): {spec.cta_text}")
    if spec.layout_notes:
        copy_lines.append(f"Layout hint: {spec.layout_notes}")
    copy_block = "\n".join(copy_lines) if copy_lines else "No explicit copy; use campaign concept."

    brand_lines: list[str] = []
    if palette:
        brand_lines.append(f"Brand palette (use these hex values exactly): {palette}")
    if typography:
        brand_lines.append(f"Typography (reference by fontFamily): {typography}")
    if visual_direction:
        brand_lines.append(f"Visual direction: {visual_direction}")
    if archetype:
        brand_lines.append(f"Brand archetype: {archetype}")
    brand_block = "\n".join(brand_lines) if brand_lines else ""

    return (
        f"Design a {asset_type} ({spec.format}) for a real brand campaign.\n"
        f"Target render size: {width_px}px x {height_px}px.\n\n"
        f"Campaign concept: {campaign_concept.strip() or 'product launch'}\n\n"
        f"{copy_block}\n\n"
        f"{brand_block}\n\n"
        "Return ONLY a single ``function Asset() { return (...); }`` block. "
        "No markdown fences, no prose, no imports."
    )


_FENCE_RE = re.compile(r"^```(?:jsx|tsx|javascript|js)?\s*\n?(.*?)\n?```$", re.DOTALL)


def _clean_jsx_source(raw: str) -> str:
    """Strip markdown fences / leading prose so the result is runnable.

    LLMs routinely wrap code in ```jsx ... ``` fences despite being told not
    to. Stripping defensively saves a re-prompt. We also cut anything before
    the first ``function`` keyword — stray "Here is the component:" prefaces
    are common.
    """
    text = (raw or "").strip()
    if not text:
        return ""
    fence_match = _FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    function_idx = text.find("function ")
    if function_idx > 0:
        # Everything before `function` is prose / imports we don't want.
        text = text[function_idx:].strip()
    return text


async def _design_one(
    *,
    index: int,
    spec: AssetSpec,
    brand_identity: dict[str, Any],
    campaign_concept: str,
) -> tuple[str, dict[str, Any]]:
    """Generate JSX for a single asset spec. Returns ``(jsx_code, metadata)``.

    Never raises: a failed design for one asset shouldn't block the others.
    The caller inspects ``metadata['status']`` to decide on follow-up.
    """
    width_px, height_px = _dimensions_for(spec)
    prompt = _build_design_prompt(
        spec=spec,
        brand_identity=brand_identity,
        campaign_concept=campaign_concept,
        width_px=width_px,
        height_px=height_px,
    )

    try:
        raw, gen_metadata = await generate_text(
            system_prompt=DESIGN_SYSTEM_PROMPT,
            user_prompt=prompt,
            model_tier="creative",
            temperature=0.4,
        )
    except Exception as exc:
        logger.warning(
            "creative_asset: spec #%s (%s, %s) design failed: %s",
            index,
            spec.asset_type,
            spec.format,
            exc,
        )
        return "", {
            "index": index,
            "asset_type": spec.asset_type,
            "format": spec.format,
            "status": "error",
            "error": str(exc),
        }

    jsx_code = _clean_jsx_source(raw)
    if not jsx_code or "function Asset" not in jsx_code:
        logger.warning(
            "creative_asset: spec #%s (%s, %s) returned non-JSX payload: %r",
            index,
            spec.asset_type,
            spec.format,
            (raw or "")[:200],
        )
        return "", {
            "index": index,
            "asset_type": spec.asset_type,
            "format": spec.format,
            "status": "skipped",
            "reason": "designer returned no valid JSX",
            "model_metadata": gen_metadata,
        }

    return jsx_code, {
        "index": index,
        "asset_type": spec.asset_type,
        "format": spec.format,
        "status": "ok",
        "width_px": width_px,
        "height_px": height_px,
        "model_metadata": gen_metadata,
    }


async def _design_specs(
    *,
    campaign: CreativeCampaign,
    brand_identity: dict[str, Any],
    on_progress: Any = None,
) -> list[dict[str, Any]]:
    """Run the designer pass on every spec in parallel, emitting progress.

    Writes ``jsx_code`` / dimensions back onto each spec in place, then pushes
    a fresh campaign snapshot through ``on_progress`` so the posters & flyers
    page can fill in one card at a time.
    """
    specs = campaign.asset_specs
    lock = asyncio.Lock()

    async def _run_one(index: int, spec: AssetSpec) -> dict[str, Any]:
        # Lock in the target dimensions on the spec up front so the frontend
        # can already draw correctly-proportioned placeholder cards while the
        # designer is still writing the JSX.
        width_px, height_px = _dimensions_for(spec)
        spec.width_px = width_px
        spec.height_px = height_px

        jsx_code, outcome = await _design_one(
            index=index,
            spec=spec,
            brand_identity=brand_identity,
            campaign_concept=campaign.campaign_concept,
        )
        if jsx_code:
            spec.jsx_code = jsx_code
            spec.status = "ok"
        else:
            spec.status = "error"

        # Serialise progress emission so the draft artifact writes stay
        # ordered — parallel writes would otherwise risk clobbering each
        # other's spec updates.
        if on_progress is not None:
            async with lock:
                try:
                    await on_progress(campaign.model_dump(mode="json"))
                except Exception:
                    logger.warning(
                        "creative_asset: progress emit for spec #%s failed",
                        index,
                        exc_info=True,
                    )
        return outcome

    return await asyncio.gather(*(_run_one(i, s) for i, s in enumerate(specs)))


# ── Single-asset helpers for the on-demand "imagine" flow ──────────────────

_IMAGINE_COPY_SYSTEM_PROMPT = """You are a creative director writing copy for a SINGLE brand asset.

Given a brand strategy, brand identity, and a short user prompt describing
what they want, return ONE asset specification: a headline (2-6 words, punchy),
short body copy (one sentence), a single CTA label (2-4 words), and terse
layout notes (how the designer should compose the asset). Respect the brand
voice. Do not repeat the prompt verbatim — interpret it."""


class _ImagineCopy(BaseModel):
    headline: str
    body_copy: str = ""
    cta_text: str = ""
    layout_notes: str = ""


async def write_copy_for_prompt(
    *,
    user_prompt: str,
    asset_type: str,
    asset_format: str,
    strategy: dict[str, Any],
    brand_identity: dict[str, Any],
) -> AssetSpec:
    """Turn a free-form user prompt into a fully-formed ``AssetSpec``.

    Used by the on-demand imagine flow: the user types a short brief, we run
    the copywriter on just that one asset, and hand the result to the
    designer. No ``jsx_code`` yet — the caller follows up with
    ``design_one_asset``.
    """
    prompt = (
        f"User prompt: {user_prompt.strip()}\n\n"
        f"Asset type: {asset_type}\n"
        f"Format: {asset_format}\n\n"
        f"Strategy (for voice + positioning): {json.dumps(strategy)[:4000]}\n\n"
        f"Brand identity (for design tokens): {json.dumps(brand_identity)[:4000]}"
    )
    copy, _ = await generate_structured(
        system_prompt=_IMAGINE_COPY_SYSTEM_PROMPT,
        user_prompt=prompt,
        response_model=_ImagineCopy,
        model_tier="creative",
        temperature=0.6,
    )
    spec = AssetSpec(
        asset_type=asset_type,
        format=asset_format,
        headline=copy.headline,
        body_copy=copy.body_copy or None,
        cta_text=copy.cta_text or None,
        layout_notes=copy.layout_notes or None,
        status="pending",
    )
    width_px, height_px = _dimensions_for(spec)
    spec.width_px = width_px
    spec.height_px = height_px
    return spec


async def design_one_asset(
    *,
    spec: AssetSpec,
    brand_identity: dict[str, Any],
    campaign_concept: str,
) -> tuple[str, dict[str, Any]]:
    """Public wrapper around ``_design_one`` for the on-demand imagine flow.

    Returns ``(jsx_code, metadata)`` — never raises. The caller mutates the
    spec's ``jsx_code`` / ``status`` fields itself so the DB write stays
    in their hands.
    """
    return await _design_one(
        index=0,
        spec=spec,
        brand_identity=brand_identity,
        campaign_concept=campaign_concept,
    )


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
    on_progress: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del project  # project identity isn't used now that we don't upload files

    strategy = inputs.get(ArtifactType.STRATEGY, {})
    brand_identity = inputs.get(ArtifactType.BRAND_IDENTITY, {})

    # ── Phase 1: copywriter ──────────────────────────────────────────────
    user_prompt = f"""Create a launch campaign for this brand.

Strategy (use taglines, voice_rules, positioning, and key_messages):
{json.dumps(strategy, indent=2)}

Brand identity (apply the design tokens and visual direction to asset specs):
{json.dumps(brand_identity, indent=2)}

Generate campaign concept, copy for poster/flyer/social, email subject lines, and asset specs.
Leave jsx_code on each asset_spec empty — the designer phase fills that in."""

    campaign, copy_metadata = await generate_structured(
        system_prompt=COPY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=CreativeCampaign,
        model_tier="creative",
        temperature=0.5,
    )

    # Publish copy immediately so the posters & flyers page can draw
    # placeholder cards with the real headline/body/CTA while the designer
    # pass chugs through.
    if on_progress is not None:
        await on_progress(campaign.model_dump(mode="json"))

    # ── Phase 2: designer (JSX per asset) ────────────────────────────────
    design_metadata: list[dict[str, Any]] = []
    if campaign.asset_specs:
        design_metadata = await _design_specs(
            campaign=campaign,
            brand_identity=brand_identity,
            on_progress=on_progress,
        )

    designed_count = sum(1 for m in design_metadata if m.get("status") == "ok")
    failed_count = sum(1 for m in design_metadata if m.get("status") == "error")

    metadata: dict[str, Any] = {
        "copywriter": copy_metadata,
        "designer": {
            "total": len(design_metadata),
            "designed": designed_count,
            "failed": failed_count,
            "results": design_metadata,
        },
    }
    return campaign.model_dump(mode="json"), metadata
