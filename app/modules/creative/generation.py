"""Poster generation helpers."""

import re
from collections.abc import AsyncIterator
from typing import Literal

from app.core.config import get_settings
from app.shared.generation_schemas import GenerationBrandContext, GenerationMessage
from app.shared.services.llm_streaming import create_text_stream_with_fallback

MAX_REFERENCE_IMAGES = 3
MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024
DATA_URL_PATTERN = re.compile(r"^data:([a-zA-Z0-9./+\-]+);base64,([A-Za-z0-9+/=]+)$")


class ValidReferenceImage(dict):
    name: str
    mime_type: str
    data_url: str
    base64_data: str


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


def build_poster_system_prompt(
    *,
    brand_context: GenerationBrandContext | None,
    generation_mode: Literal["auto", "manual"] = "manual",
) -> str:
    is_auto = generation_mode == "auto"
    filenames = "\n".join(
        [
            "- /poster-v1-4x5.tsx",
            "- /poster-v1-9x16.tsx",
            "- /poster-v1-16x9.tsx",
            "- /poster-v1-1x1.tsx",
        ]
        if not is_auto
        else [
            "- /poster-v1-4x5.tsx",
            "- /poster-v1-9x16.tsx",
            "- /poster-v1-16x9.tsx",
            "- /poster-v1-1x1.tsx",
            "- /poster-v2-4x5.tsx",
            "- /poster-v2-9x16.tsx",
            "- /poster-v2-16x9.tsx",
            "- /poster-v2-1x1.tsx",
            "- /poster-v3-4x5.tsx",
            "- /poster-v3-9x16.tsx",
            "- /poster-v3-16x9.tsx",
            "- /poster-v3-1x1.tsx",
            "- /poster-v4-4x5.tsx",
            "- /poster-v4-9x16.tsx",
            "- /poster-v4-16x9.tsx",
            "- /poster-v4-1x1.tsx",
        ]
    )
    variation_block = (
        "- Generate four variants: brutal truth, clever twist, proof-led, editorial premium."
        if is_auto
        else "- Generate one strongest concept only."
    )
    extra_files_rule = "16" if is_auto else "4"

    return f"""You are Klaro, an award-winning direct-response poster designer.

GOAL
- Create posters that are understood in 3 seconds.
- One clear promise, one clear CTA, high legibility.
- Prioritize hierarchy and conversion over decoration.

MODE SELECTION
- If the user has not given enough context about audience, offer, or CTA, ask only 1-2 short questions and stop.
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

COPY RULES
- Headline should read instantly.
- Avoid jargon and fake hype.
- Use believable specificity and proof.
- One CTA only.

DESIGN RULES
- Big type, strong contrast, clean composition.
- Safe margins for every format.
- 9x16 must keep critical copy away from the top and bottom UI zones.
- 16x9 should use horizontal hierarchy.

VARIATION RULES
{variation_block}

DO NOT
- Do not add extra files beyond the required {extra_files_rule}.
- Do not output explanations outside <summary> and <file> tags.

{_brand_section(brand_context)}
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
    brand_context: GenerationBrandContext | None,
    reference_images: list[dict[str, str]],
    generation_mode: Literal["auto", "manual"],
) -> AsyncIterator[str]:
    settings = get_settings()
    max_tokens = max(4096, min(20000, settings.poster_max_output_tokens))
    system_prompt = build_poster_system_prompt(
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
