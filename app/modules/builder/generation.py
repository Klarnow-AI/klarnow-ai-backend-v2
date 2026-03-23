"""Website generation helpers for builder projects."""

from collections.abc import AsyncIterator
from typing import Literal

from app.shared.generation_schemas import GenerationBrandContext, GenerationMessage
from app.shared.services.llm_streaming import create_text_stream
from app.shared.services.openai_compatible import (
    get_builder_model,
    get_reasoning_model,
)


_DEFAULT_APP_MARKER = "Describe your website to get started"
_MIN_COMPLETION_TOKENS = 2048
BuilderAssistantMode = Literal["launch", "convert", "polish", "debug"]
_DESIGN_SYSTEM_TOKENS = {
    "minimal": """
- Mood: editorial, calm, intentional, premium without feeling sterile
- Background: warm neutrals, subtle panel layering, restrained gradients
- Typography: elegant sans or serif pairing with generous spacing
- Shapes: rounded-xl where useful, otherwise let whitespace do the work
- Motion: subtle fades and hover shifts only
""",
    "dark": """
- Mood: cinematic, high-contrast, immersive
- Background: charcoal or ink with depth from glows, gradients, and overlays
- Typography: oversized, dramatic, crisp
- Shapes: strong cards, bold framing, clean spacing
- Motion: tasteful reveal transitions and depth cues
""",
    "playful": """
- Mood: bright, friendly, energetic, modern
- Background: soft tints, layered gradients, unexpected accents
- Typography: approachable with bold moments
- Shapes: soft curves, pill controls, rounded-3xl moments
- Motion: lively but not childish
""",
    "corporate": """
- Mood: crisp, credible, executive, confident
- Background: white, slate, or light neutral with strong structure
- Typography: trustworthy, balanced, slightly condensed if it helps hierarchy
- Shapes: precise grids, restrained rounding
- Trust signals: logos, proof, process clarity, concise metrics
""",
    "luxury": """
- Mood: elevated, tactile, exclusive
- Background: off-black, stone, espresso, or cream
- Typography: refined contrast, careful letter spacing, gallery-like pacing
- Shapes: sharp lines or lightly rounded premium framing
- Motion: restrained, polished, expensive
""",
    "vibrant": """
- Mood: bold, graphic, creative-forward
- Background: saturated fields, meshes, or contrast-heavy color blocking
- Typography: expressive and assertive
- Shapes: confident cards, oversized sections, energetic composition
- Motion: bold reveals and hover treatments with restraint
""",
}


def is_default_files(files: dict[str, str]) -> bool:
    if len(files) != 1:
        return False
    content = files.get("/App.tsx") or files.get("App.tsx") or ""
    return _DEFAULT_APP_MARKER in content


def _resolve_thinking_budget(max_tokens: int, requested_budget: int | None) -> int | None:
    if requested_budget is None or requested_budget <= 0:
        return None

    max_budget = max_tokens - _MIN_COMPLETION_TOKENS
    if max_budget <= 0:
        max_budget = max_tokens - 1
    if max_budget <= 0:
        return None
    return min(requested_budget, max_budget)


def _brand_section(brand: GenerationBrandContext | None) -> str:
    if brand is None:
        return ""

    sections: list[str] = []
    identity: list[str] = []
    messaging: list[str] = []
    audience: list[str] = []
    style: list[str] = []

    if brand.brand_name:
        identity.append(f"Brand name: {brand.brand_name}")
    if brand.industry:
        identity.append(f"Industry: {brand.industry}")
    if brand.target_audience:
        identity.append(f"Target audience: {brand.target_audience}")
    if brand.main_audience:
        identity.append(f"Main audience signals: {', '.join(brand.main_audience)}")
    if brand.logo_url:
        identity.append(f"Logo URL: {brand.logo_url}")
    if brand.logo_markup:
        identity.append("Logo markup is available for inline SVG treatment.")
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
            identity.append(f"Brand colors: {', '.join(colors)}")
    if brand.fonts:
        identity.append(f"Preferred fonts: {', '.join(brand.fonts)}")
    if identity:
        sections.append("BRAND IDENTITY:\n" + "\n".join(identity))

    for label, value in (
        ("Core offer", brand.core_offer),
        ("Primary CTA", brand.primary_cta),
        ("Primary pain", brand.primary_pain),
        ("Primary outcome", brand.primary_outcome),
        ("Hero angle", brand.hero_angle),
        ("USP", brand.usp_statement),
        ("USP proof", brand.usp_proof),
        ("Brand promise", brand.promise),
        ("Mission", brand.mission),
        ("Vision", brand.vision),
        ("Elevator pitch", brand.elevator_pitch),
    ):
        if value:
            messaging.append(f"{label}: {value}")
    if brand.brand_purpose:
        messaging.append("Brand purpose:\n- " + "\n- ".join(brand.brand_purpose))
    if brand.proof_points:
        messaging.append("Proof points:\n- " + "\n- ".join(brand.proof_points))
    if messaging:
        sections.append("MESSAGING:\n" + "\n".join(messaging))

    if brand.audience_personas:
        for persona in brand.audience_personas:
            parts = [f"Persona: {persona.persona}"]
            if persona.needs:
                parts.append("Needs: " + ", ".join(persona.needs))
            if persona.pain_points:
                parts.append("Pain points: " + ", ".join(persona.pain_points))
            audience.append("\n".join(parts))
    if audience:
        sections.append("AUDIENCE:\n" + "\n\n".join(audience))

    if brand.voice_archetype:
        style.append(f"Voice archetype: {brand.voice_archetype}")
    if brand.voice_traits:
        style.append("Voice traits: " + ", ".join(brand.voice_traits))
    if brand.design_cues:
        style.append("Design cues: " + ", ".join(brand.design_cues))
    if brand.style_palette:
        style.append("Palette language: " + ", ".join(brand.style_palette))
    if brand.typography_direction:
        style.append(f"Typography direction: {brand.typography_direction}")
    if style:
        sections.append("VOICE AND STYLE:\n" + "\n".join(style))

    return "\n\nBRAND CONTEXT:\n" + "\n\n".join(sections) if sections else ""


def _industry_template(brand: GenerationBrandContext | None) -> str:
    combined = " ".join(
        part.lower()
        for part in (
            brand.industry if brand else None,
            brand.core_offer if brand else None,
            brand.hero_angle if brand else None,
            brand.primary_pain if brand else None,
        )
        if part
    )
    if not combined:
        return ""

    if any(word in combined for word in ("saas", "software", "app", "platform", "api", "tool")):
        return """
INDUSTRY SHAPE:
- Hero with one problem-first headline and product visual.
- Features grid focused on outcomes, not labels.
- Trust row with logos or customer proof.
- Pricing section and FAQ.
"""
    if any(word in combined for word in ("agency", "marketing", "consulting", "studio", "freelance")):
        return """
INDUSTRY SHAPE:
- Hero with positioning statement.
- Services section.
- Process section with 3-4 steps.
- Case studies or proof.
- Strong consultation CTA.
"""
    if any(word in combined for word in ("ecommerce", "shop", "store", "retail", "fashion", "product")):
        return """
INDUSTRY SHAPE:
- Hero with product or collection focus.
- Featured products grid.
- Social proof and value props.
- FAQ and conversion CTA.
"""
    return ""


def _design_system_section(selected_style: str | None) -> str:
    if not selected_style:
        return ""
    tokens = _DESIGN_SYSTEM_TOKENS.get(selected_style.strip().lower())
    if not tokens:
        return ""
    return "\n\nSELECTED DESIGN SYSTEM:\n" + tokens.strip()


def _assistant_mode_section(assistant_mode: BuilderAssistantMode | None) -> str:
    mode = (assistant_mode or "launch").strip().lower()
    if mode == "convert":
        return """

ASSISTANT MODE: CONVERT
- Prioritize clarity, trust, CTA visibility, and lead capture quality.
- Tighten the funnel: objection handling, proof, and friction reduction.
- Prefer stronger copy and cleaner conversion pathways over decorative extras.
"""
    if mode == "polish":
        return """

ASSISTANT MODE: POLISH
- Prioritize visual refinement, spacing rhythm, typography, and premium finish.
- Improve hierarchy and craft without losing clarity or conversion intent.
- Make the page feel contemporary and intentional, not template-like.
"""
    if mode == "debug":
        return """

ASSISTANT MODE: DEBUG
- Fix the specific issue with minimal disruption to the rest of the design.
- Preserve working sections unless the bug requires structural changes.
- Return a stable, corrected file without explaining internal debugging steps.
"""
    return """

ASSISTANT MODE: LAUNCH
- Make strong, opinionated product and design decisions without stalling.
- Deliver the best credible first version you can from the available context.
- When direction is partial, fill the gaps with tasteful, conversion-focused choices.
"""


def build_system_prompt(
    *,
    files: dict[str, str],
    brand_context: GenerationBrandContext | None,
    selected_style: str | None,
    assistant_mode: BuilderAssistantMode | None,
) -> str:
    current_files = "\n\n".join(
        f'<file name="{name}">\n{content}\n</file>'
        for name, content in files.items()
    )
    discovery_mode = is_default_files(files)
    brand_name = brand_context.brand_name if brand_context else None

    if discovery_mode:
        mode_block = f"""
DISCOVERY MODE:
- If the user has not already given enough direction, ask 2-3 targeted questions.
- Use this exact XML format:
<summary>Brief acknowledgment{f' for {brand_name}' if brand_name else ''}.</summary>
<questions>
<q type="select" options="Hero + Features + CTA,Hero + Features + Social Proof + CTA,Hero + Features + Pricing + Testimonials + CTA,Full page">How complete should the first version be?</q>
<q type="select" options="Clean & minimal,Bold & dark,Soft & playful,Corporate & professional,Luxury & premium,Vibrant & creative">What visual style fits best?</q>
<q type="text" placeholder="must-have sections, colors, references, or things to avoid">Anything specific to include or avoid?</q>
</questions>
- If the user clearly wants you to build now, skip questions and build immediately.
- Do not output any <file> tags when asking questions.
"""
    else:
        mode_block = """
BUILD MODE:
- Read the current files carefully before making changes.
- If the user reports an error, fix the exact bug and return the complete corrected file.
- If the user asks for a vague improvement, make the strongest visible improvement without asking.
"""

    return f"""You are Klaro, an expert React + Tailwind website builder.

GOAL
- Produce a polished, production-ready single-page website in /App.tsx.
- Use clear hierarchy, strong conversion copy, and responsive layout.
- Keep the page deployable inside the existing builder runtime.
- Use the available brand context deeply so the page feels custom, not generic.

OUTPUT RULES
- Output ONLY XML tags. No markdown.
- When asking questions:
<summary>One short sentence.</summary>
<questions>
<q type="select" options="A,B,C">Question?</q>
</questions>
- When building or editing:
<summary>One short sentence describing the change.</summary>
<file name="/App.tsx">
// complete file content
</file>

TECHNICAL RULES
- React with TypeScript.
- Tailwind CSS only.
- Keep all sections and helpers in /App.tsx.
- No external component libraries.
- Use emoji instead of icon packages when needed.
- Defensive code only: avoid undefined.map(), use keys in every .map().
- Always return the full file, never partial patches.
- Prefer a layered, modern visual system over flat boilerplate.
- Use CSS variables or small shared constants when it helps keep the design cohesive.

LEAD CAPTURE RULES
- Any contact, signup, booking, or enquiry form must submit to window.KLARO_LEAD_URL with fetch.
- Collect name plus email or phone.
- Include a hidden honeypot input named website.
- Show success and error states.
- Support JSON submission and keep field names predictable.

QUALITY BAR
- Clear value prop above the fold.
- Specific copy, no lorem ipsum.
- Mobile-first layout.
- Visible CTA.
- Trust elements when relevant.
- Avoid generic startup templates, repetitive card grids, and lifeless whitespace-only layouts.
- Build a visual point of view: strong hero composition, contrast, and section-to-section rhythm.
- Make typography, color, and spacing feel deliberate and current.

{mode_block}
{_assistant_mode_section(assistant_mode)}
{_brand_section(brand_context)}
{_industry_template(brand_context)}
{_design_system_section(selected_style)}

CURRENT PROJECT FILES:
{current_files}
"""


async def create_website_generation_stream(
    *,
    messages: list[GenerationMessage],
    files: dict[str, str],
    brand_context: GenerationBrandContext | None,
    selected_style: str | None,
    assistant_mode: BuilderAssistantMode | None = None,
) -> AsyncIterator[str]:
    generation_mode = is_default_files(files)
    system_prompt = build_system_prompt(
        files=files,
        brand_context=brand_context,
        selected_style=selected_style,
        assistant_mode=assistant_mode,
    )
    max_tokens = 8192
    primary_model = get_builder_model() if generation_mode else get_reasoning_model()

    messages_payload = [
        {"role": message.role, "content": message.content}
        for message in messages
    ]
    return await create_text_stream(
        system_prompt=system_prompt,
        messages=messages_payload,
        model=primary_model,
        max_tokens=max_tokens,
    )
