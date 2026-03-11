"""Poster generation helpers."""

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings
from app.shared.generation_schemas import GenerationBrandContext, GenerationMessage
from app.shared.services.llm_streaming import create_text_stream_with_fallback

MAX_REFERENCE_IMAGES = 3
MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024
DATA_URL_PATTERN = re.compile(r"^data:([a-zA-Z0-9./+\-]+);base64,([A-Za-z0-9+/=]+)$")
MASTER_SOCIAL_DIMENSIONS = "4:5 portrait (1080×1350px, vertical social media format)"
SHARED_CREATIVE_SYSTEM_PROMPT = (
    "You are a creative director. Generate a single stunning marketing poster image based on the brief. "
    "The image should look like a professional advertising campaign visual."
)
PROOF_FALLBACK = (
    "No proof provided — invent a realistic, specific credibility element "
    "(e.g. '2,847 happy clients' or a short testimonial quote)."
)

VARIANT_INSTRUCTIONS: dict[str, str] = {
    "A": (
        "Variant A: HEADLINE FRAMING — bold, oversized headline at an angle or stacked vertically. "
        "Think editorial magazine cover with punchy text that stops the scroll."
    ),
    "B": (
        "Variant B: LIFESTYLE COMPOSITION — arrange text around an imagined product/lifestyle scene. "
        "Layered typography with mixed weights and sizes, like a fashion or food brand campaign."
    ),
    "C": (
        "Variant C: PROOF-LED DESIGN — make the social proof, testimonial, or result the hero element. "
        "Bold quote styling, large numbers, before/after visual treatment."
    ),
}

TEMPLATE_PROMPTS: dict[str, str] = {
    "offer": (
        "This is an OFFER poster — the main offer/deal should be the hero element. "
        "Bold price or value proposition front and center. Make it feel like a premium brand campaign, "
        "not a discount flyer."
    ),
    "proof": (
        "This is a PROOF poster — lead with a testimonial, review quote, or before/after result. "
        "Social proof is the hero. Style it like an editorial feature."
    ),
    "objection": (
        "This is an OBJECTION BUSTER poster — address and overcome a common objection. "
        "Use bold contrast between the myth and reality. Provocative and attention-grabbing."
    ),
}

POSTER_SIZE_SPECS: tuple[tuple[str, int, int, str], ...] = (
    ("4x5", 1080, 1350, "Use this as the master composition for the concept."),
    ("9x16", 1080, 1920, "Keep critical copy away from top and bottom mobile UI zones."),
    ("16x9", 1920, 1080, "Rebuild the hierarchy horizontally for landscape."),
    ("1x1", 1080, 1080, "Compress the hierarchy without shrinking the main idea."),
)

PosterGenerationMode = Literal["auto", "manual"]
PosterTemplateKey = Literal["offer", "proof", "objection"]
PosterVariantKey = Literal["A", "B", "C"]
PosterSlotId = Literal["v1", "v2", "v3", "v4"]


class ValidReferenceImage(dict):
    name: str
    mime_type: str
    data_url: str
    base64_data: str


@dataclass(frozen=True)
class PosterPromptBrief:
    business_name: str
    offer: str
    usp: str
    cta: str
    proof_line: str
    business_type: str
    tone: str


@dataclass(frozen=True)
class PosterSlotConfig:
    slot_id: PosterSlotId
    template_key: PosterTemplateKey
    variant_key: PosterVariantKey


MANUAL_SLOT_CONFIGS: tuple[PosterSlotConfig, ...] = (
    PosterSlotConfig(slot_id="v1", template_key="offer", variant_key="A"),
)

AUTO_SLOT_CONFIGS: tuple[PosterSlotConfig, ...] = (
    PosterSlotConfig(slot_id="v1", template_key="objection", variant_key="A"),
    PosterSlotConfig(slot_id="v2", template_key="offer", variant_key="B"),
    PosterSlotConfig(slot_id="v3", template_key="proof", variant_key="C"),
    PosterSlotConfig(slot_id="v4", template_key="offer", variant_key="A"),
)


def estimate_base64_bytes(base64_data: str) -> int:
    padding = 2 if base64_data.endswith("==") else 1 if base64_data.endswith("=") else 0
    return max(0, ((len(base64_data) * 3) // 4) - padding)


def normalize_reference_images(images: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not images:
        return []
    if len(images) > MAX_REFERENCE_IMAGES:
        raise ValueError(f"You can attach up to {MAX_REFERENCE_IMAGES} reference images.")

    normalized: list[dict[str, str]] = []
    for index, image in enumerate(images):
        name = str(image.get("name") or "").strip() or f"image-{index + 1}"
        mime_type = str(image.get("mime_type") or image.get("mimeType") or "").strip().lower()
        data_url = str(image.get("data_url") or image.get("dataUrl") or "").strip()

        if not mime_type.startswith("image/"):
            raise ValueError(f"referenceImages[{index}] must be an image mime type.")

        match = DATA_URL_PATTERN.match(data_url)
        if not match:
            raise ValueError(f"referenceImages[{index}] has an invalid dataUrl format.")

        data_url_mime = match.group(1).lower()
        base64_data = match.group(2)
        if not data_url_mime.startswith("image/"):
            raise ValueError(f"referenceImages[{index}] dataUrl must be an image.")
        if estimate_base64_bytes(base64_data) > MAX_REFERENCE_IMAGE_BYTES:
            raise ValueError(f"referenceImages[{index}] is larger than 4MB.")

        normalized.append(
            {
                "name": name,
                "mime_type": data_url_mime,
                "data_url": data_url,
                "base64_data": base64_data,
            }
        )
    return normalized


def _clean_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_non_empty(values: list[str] | None) -> str:
    if not values:
        return ""
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _coalesce_text(*values: object | None, default: str = "") -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return default


def resolve_poster_prompt_brief(
    *,
    pack,
    brand_context: GenerationBrandContext | None,
) -> PosterPromptBrief:
    business_name = _coalesce_text(
        getattr(pack, "brand_name", None),
        getattr(pack, "name", None),
        default="Business",
    )
    offer = _coalesce_text(
        getattr(pack, "offer_one_liner", None),
        getattr(brand_context, "core_offer", None) if brand_context else None,
        default="Our offer",
    )
    usp = _coalesce_text(
        getattr(pack, "usp_locked_line", None),
        getattr(pack, "usp_statement", None),
        getattr(brand_context, "usp_statement", None) if brand_context else None,
        default="",
    )
    cta = _coalesce_text(
        getattr(pack, "primary_cta", None),
        default="Learn more",
    )
    proof_value = _coalesce_text(
        getattr(pack, "proof_text", None),
        _first_non_empty(brand_context.proof_points) if brand_context else None,
        getattr(pack, "usp_proof", None),
    )
    proof_line = (
        f'Proof/testimonial: "{proof_value}"'
        if proof_value
        else PROOF_FALLBACK
    )
    business_type = _coalesce_text(
        getattr(pack, "business_type", None),
        getattr(brand_context, "industry", None) if brand_context else None,
        default="business",
    )
    tone = _coalesce_text(
        getattr(brand_context, "voice_archetype", None) if brand_context else None,
        default="bold, confident, premium",
    )

    return PosterPromptBrief(
        business_name=business_name,
        offer=offer,
        usp=usp,
        cta=cta,
        proof_line=proof_line,
        business_type=business_type,
        tone=tone,
    )


def get_poster_slot_configs(generation_mode: PosterGenerationMode) -> tuple[PosterSlotConfig, ...]:
    return AUTO_SLOT_CONFIGS if generation_mode == "auto" else MANUAL_SLOT_CONFIGS


def _brand_section(brand: GenerationBrandContext | None) -> str:
    if brand is None:
        return ""

    lines: list[str] = []
    for label, value in (
        ("Brand name", brand.brand_name),
        ("Industry", brand.industry),
        ("Core offer", brand.core_offer),
        ("Primary CTA", brand.primary_cta),
        ("Primary pain", brand.primary_pain),
        ("Primary outcome", brand.primary_outcome),
        ("Hero angle", brand.hero_angle),
        ("USP", brand.usp_statement),
        ("USP proof", brand.usp_proof),
        ("Mission", brand.mission),
        ("Vision", brand.vision),
        ("Elevator pitch", brand.elevator_pitch),
    ):
        if value:
            lines.append(f"{label}: {value}")

    if brand.color_palette:
        colors = [
            f"{name}: {value}"
            for name, value in (
                ("primary", brand.color_palette.primary),
                ("secondary", brand.color_palette.secondary),
                ("accent", brand.color_palette.accent),
            )
            if value
        ]
        if colors:
            lines.append(f"Brand colors: {', '.join(colors)}")
    if brand.fonts:
        lines.append(f"Fonts: {', '.join(brand.fonts)}")
    if brand.logo_url:
        lines.append(f"Logo URL: {brand.logo_url}")
    if brand.logo_markup:
        lines.append("Logo SVG Markup:\n" + brand.logo_markup)
    if brand.proof_points:
        lines.append("Proof points:\n- " + "\n- ".join(brand.proof_points))
    if brand.audience_personas:
        persona_lines = []
        for persona in brand.audience_personas:
            parts = [f"Persona: {persona.persona}"]
            if persona.needs:
                parts.append("Needs: " + ", ".join(persona.needs))
            if persona.pain_points:
                parts.append("Pain points: " + ", ".join(persona.pain_points))
            persona_lines.append("\n".join(parts))
        if persona_lines:
            lines.append("Audience:\n" + "\n\n".join(persona_lines))
    if brand.voice_archetype:
        lines.append(f"Voice archetype: {brand.voice_archetype}")
    if brand.design_cues:
        lines.append("Design cues: " + ", ".join(brand.design_cues))

    return "\n\nBRAND CONTEXT:\n" + "\n".join(lines) if lines else ""


def _logo_rules(brand: GenerationBrandContext | None) -> str:
    if brand is None or (not brand.logo_url and not brand.logo_markup):
        return (
            "LOGO RULES\n"
            "- No brand logo asset was provided. Use a clean brand-name text lockup only if needed."
        )

    rules = [
        "LOGO RULES",
        "- A brand logo asset is available from Brand Identity and must appear visibly in every generated poster/flyer file.",
        "- Use the exact provided brand logo asset. Do not replace it with plain text, a fake logo, or a newly invented mark.",
        "- Place the logo in a clean lockup area near the top or bottom with strong contrast and clear breathing room.",
    ]
    if brand.logo_url:
        rules.append(
            f'- For URL logos, use an actual image tag with src="{brand.logo_url}", '
            'loading="eager", and referrerPolicy="no-referrer".'
        )
    if brand.logo_markup:
        rules.append(
            "- For inline SVG logos, embed the provided SVG markup directly in the TSX, "
            "for example with dangerouslySetInnerHTML or equivalent inline SVG output."
        )
    return "\n".join(rules)


def _build_required_filenames(slot_configs: tuple[PosterSlotConfig, ...]) -> str:
    file_lines: list[str] = []
    for slot in slot_configs:
        for size_id, _, _, _ in POSTER_SIZE_SPECS:
            file_lines.append(f"- /poster-{slot.slot_id}-{size_id}.tsx")
    return "\n".join(file_lines)


def _build_size_rules(slot_configs: tuple[PosterSlotConfig, ...]) -> str:
    size_lines: list[str] = [
        "- Treat the shared creative block for each slot as the master concept for the 4:5 poster.",
        "- Adapt that same concept for every other required size in the slot.",
    ]
    for slot in slot_configs:
        for size_id, width, height, note in POSTER_SIZE_SPECS:
            size_lines.append(
                f"- /poster-{slot.slot_id}-{size_id}.tsx: root artboard must be {width}x{height}. {note}"
            )
    return "\n".join(size_lines)


def _build_slot_mapping(slot_configs: tuple[PosterSlotConfig, ...]) -> str:
    return "\n".join(
        f"- {slot.slot_id}: template={slot.template_key}, variant={slot.variant_key}"
        for slot in slot_configs
    )


def build_shared_creative_prompt_block(
    *,
    brief: PosterPromptBrief,
    slot_config: PosterSlotConfig,
) -> str:
    template_instruction = TEMPLATE_PROMPTS[slot_config.template_key]
    variant_instruction = VARIANT_INSTRUCTIONS[slot_config.variant_key]

    return f"""You are a world-class creative director at a top advertising agency. Create a stunning, scroll-stopping marketing poster image.

BRAND: {brief.business_name}
OFFER: {brief.offer}
USP: {brief.usp}
CTA: {brief.cta}
{brief.proof_line}
Business type: {brief.business_type}
Tone: {brief.tone}

FORMAT: {MASTER_SOCIAL_DIMENSIONS}

{template_instruction}

{variant_instruction}

DESIGN DIRECTION — Reference these scroll-stopping ad styles:
- BOLD OVERSIZED TYPOGRAPHY: Think KFC Treats "YOU DESERVE A TREAT" style — massive, stacked, slightly rotated text that dominates the composition. Mixed font weights. Text as a design element, not just information.
- EDITORIAL MAGAZINE FEEL: Like festival posters — big hero text at top, supporting copy at bottom, clean hierarchy. Professional photography vibe.
- PREMIUM BRAND CAMPAIGNS: Like Pinterest Academy ads — clean backgrounds, floating UI elements, red accent CTAs, sophisticated color palettes (deep blues, rich blacks, warm creams).
- PROVOCATIVE & MINIMAL: Like DTS "FILTHY VISUALS / CLEAN LICENSING" — minimal text, maximum impact, cinematic feel, centered typography with brand mark.

CRITICAL DESIGN RULES:
1. Typography is THE star — oversized (60-120pt hero text), bold, possibly angled or stacked vertically
2. High contrast color palette — NOT generic gradients. Use intentional color blocking.
3. Clear visual hierarchy: Hero text → Supporting line → CTA badge
4. CTA should be a distinct pill/button shape in a contrasting accent color
5. Brand name/logo area at top or bottom
6. The design should look like it was made by a $50K/month creative agency
7. Include realistic textures, gradients, or photographic elements in the background
8. Make it feel like a real brand campaign poster you'd see on Instagram or a billboard
9. ONE CTA only: "{brief.cta}"
10. The poster must be in {MASTER_SOCIAL_DIMENSIONS} format — vertical/portrait orientation

COPYWRITING — Write like an experienced direct-response copywriter:
- Rewrite all copy to be PUNCHIER than the brief. Don't use brief text verbatim.
- Headlines: 2-5 words MAX. Power words. Pattern interrupts.
- Add urgency/scarcity if appropriate
- Every word must earn its place"""


def _build_slot_sections(
    *,
    brief: PosterPromptBrief,
    slot_configs: tuple[PosterSlotConfig, ...],
) -> str:
    sections: list[str] = []
    for slot in slot_configs:
        sections.append(
            f"""SLOT {slot.slot_id.upper()}
Use the following shared creative block as the master concept prompt for this slot:

{build_shared_creative_prompt_block(brief=brief, slot_config=slot)}"""
        )
    return "\n\n".join(sections)


def build_poster_system_prompt(
    *,
    pack,
    brand_context: GenerationBrandContext | None,
    generation_mode: PosterGenerationMode = "manual",
) -> str:
    slot_configs = get_poster_slot_configs(generation_mode)
    filenames = _build_required_filenames(slot_configs)
    size_rules = _build_size_rules(slot_configs)
    slot_mapping = _build_slot_mapping(slot_configs)
    brief = resolve_poster_prompt_brief(pack=pack, brand_context=brand_context)
    extra_files_rule = len(slot_configs) * len(POSTER_SIZE_SPECS)

    return f"""{SHARED_CREATIVE_SYSTEM_PROMPT}

You are returning TSX poster source files, not a raster image.

MODE SELECTION
- Ask only 1-2 short questions if the resolved brief still lacks usable brand, offer, or CTA context.
- Otherwise generate immediately.

OUTPUT FORMAT
- Output ONLY XML tags. No markdown.
- Discovery mode:
<summary>One short sentence.</summary>
- Follow with plain-language questions only, no code.
- Generation mode:
<summary>One short sentence.</summary>
<file name="/poster-v1-4x5.tsx">
// complete code
</file>

MANDATORY FILES
Return exactly these filenames:
{filenames}

FILE RULES
- Each file must be complete self-contained TSX.
- No imports.
- Use export default function ComponentName() {{ ... }}.
- Inline styles only.
- Match the named artboard size in the root element.
- Re-layout each size; do not stretch one layout.
- Use the slot mapping below exactly.

SIZE RULES
{size_rules}

CONCEPT SLOT MAPPING
{slot_mapping}

COPY RULES
- Headline should read instantly.
- Avoid jargon and fake hype.
- Use believable specificity and proof.
- One CTA only.

{_logo_rules(brand_context)}

DO NOT
- Do not add extra files beyond the required {extra_files_rule}.
- Do not output explanations outside <summary> and <file> tags.

{_brand_section(brand_context)}

{_build_slot_sections(brief=brief, slot_configs=slot_configs)}
"""


def _find_latest_user_index(messages: list[GenerationMessage]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == "user":
            return index
    return -1


def build_openai_messages(
    messages: list[GenerationMessage],
    reference_images: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not reference_images:
        return [{"role": message.role, "content": message.content} for message in messages]

    latest_user_index = _find_latest_user_index(messages)
    built: list[dict[str, object]] = []
    for index, message in enumerate(messages):
        if message.role != "user" or index != latest_user_index:
            built.append({"role": message.role, "content": message.content})
            continue
        content: list[dict[str, object]] = [{"type": "text", "text": message.content}]
        for image in reference_images:
            content.append({"type": "image_url", "image_url": {"url": image["data_url"]}})
        built.append({"role": message.role, "content": content})
    return built


def build_anthropic_messages(
    messages: list[GenerationMessage],
    reference_images: list[dict[str, str]],
) -> list[dict[str, object]]:
    if not reference_images:
        return [
            {
                "role": "assistant" if message.role == "system" else message.role,
                "content": message.content,
            }
            for message in messages
        ]

    latest_user_index = _find_latest_user_index(messages)
    built: list[dict[str, object]] = []
    for index, message in enumerate(messages):
        role = "assistant" if message.role == "system" else message.role
        if role != "user" or index != latest_user_index:
            built.append({"role": role, "content": message.content})
            continue
        content: list[dict[str, object]] = [{"type": "text", "text": message.content}]
        for image in reference_images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image["mime_type"],
                        "data": image["base64_data"],
                    },
                }
            )
        built.append({"role": role, "content": content})
    return built


async def create_poster_generation_stream(
    *,
    messages: list[GenerationMessage],
    pack,
    brand_context: GenerationBrandContext | None,
    reference_images: list[dict[str, str]],
    generation_mode: PosterGenerationMode,
) -> AsyncIterator[str]:
    settings = get_settings()
    max_tokens = max(4096, min(20000, settings.poster_max_output_tokens))
    system_prompt = build_poster_system_prompt(
        pack=pack,
        brand_context=brand_context,
        generation_mode=generation_mode,
    )
    return await create_text_stream_with_fallback(
        system_prompt=system_prompt,
        openai_messages=build_openai_messages(messages, reference_images),
        anthropic_messages=build_anthropic_messages(messages, reference_images),
        openai_model="gpt-4o",
        anthropic_model="claude-sonnet-4-6",
        max_tokens=max_tokens,
    )
