"""WebsiteBuilderAgent — plans + builds the website in one stage.

Previously this was split across ``website_planner`` (LLM call #1, reasoning
tier) and ``website_builder`` (LLM call #2, builder tier). Keeping them
separate forced the user through an extra approval gate on a plan spec that
they couldn't actually *see* rendered, and meant downstream changes required
bouncing back to the planner. The website *is* the deliverable, so planning
belongs inside the builder.

Flow inside this stage:
1. Plan phase — reasoning-tier LLM produces a :class:`WebsiteBlueprint` from
   the normalized profile + strategy + brand identity.
2. Build phase — builder-tier LLM takes that blueprint plus the brand tokens
   and emits :class:`WebsiteBuild` (pages, components, layout, globals).

The emitted artifact embeds the blueprint under ``blueprint`` so reviewers
can inspect both the plan and the code without a second artifact type.
"""

from __future__ import annotations

import json
from typing import Any

from app.modules.projects.models import Project
from app.schemas.enums import ArtifactType
from app.schemas.website_blueprint import WebsiteBlueprint
from app.schemas.website_build import WebsiteBuild
from app.modules.pipeline.model_gateway import generate_structured

PLAN_SYSTEM_PROMPT = """You are a website strategist. Given a business profile, strategy, and brand identity
(visual tokens + logo direction), create a detailed website blueprint.

The blueprint must be type-aware based on the website_type:

- landing_page: One offer, one conversion goal, single-page flow.
  Typical sections: hero, problem, solution, trust proof, CTA block, FAQ.

- brochure_static: Informational small-business website for credibility.
  Typical pages: Home, About, Services, Contact.

- service_lead_gen: Lead capture focus with service explanation and trust-building.
  Typical pages: Home, Services, About, FAQ, Contact.

For each page, define:
- Slug, title, and goal
- Sections with section_type, purpose, content notes, and CTA
- SEO title and description

Also define:
- Navigation structure
- Site map
- Global components (header, footer, etc.)
- Forms with fields and submit actions
- CTA strategy
- SEO strategy
- Design application notes

Be specific and structured. Every page and section should have a clear purpose aligned to the business goals.

Strict schema rules (do NOT break these):
- Each item in `navigation` MUST have keys `label` and `href` (NOT `slug`,
  `url`, or `path`). Example:
    {"label": "Contact", "href": "/contact"}
- Each `pages[*].sections[*].cta` MUST be a SINGLE STRING — not an object.
  If you want to express label + href + variant, fold them into one string:
    "cta": "Get in touch → /contact (primary)"
  NOT: {"label": "Get in touch", "href": "/contact", "variant": "primary"}
  If a section has no CTA, omit the key or set it to null.
- Each item in `forms` MUST have keys `name` (NOT `form_id` or `id`) and
  `purpose`, and `fields` MUST be an array of STRINGS — not objects.
  Describe each field inline as a string:
    "fields": [
      "full_name (text, required): min 2 characters",
      "email (email, required): valid email format",
      "consent (checkbox, required): must be checked"
    ]
  NOT: [{"name": "full_name", "type": "text", "required": true, ...}]
- Output must be a raw JSON object matching the schema — no wrapping in
  `properties`, no extra keys outside the schema."""


BUILD_SYSTEM_PROMPT = """You are a frontend developer. Given a website blueprint and a brand identity
(design tokens), generate a complete Next.js website.

For each page in the blueprint:
- Generate a React component using TypeScript and Tailwind CSS
- Apply the design system tokens: colors, typography, spacing, CTA styles
- Include responsive design (mobile-first)
- Use semantic HTML and accessibility best practices
- Include the page's sections as defined in the blueprint

Also generate:
- A root layout component with the navigation and footer
- Reusable components for repeated patterns (Hero, CTA, Testimonials, etc.)
- Global CSS with design token variables
- A tailwind.config.ts with the design system colors and fonts

Return structured output with the file paths and source code for each generated file.
Use App Router conventions (app/page.tsx, app/about/page.tsx, etc.).

Strict schema rules (do NOT break these):
- Do NOT re-emit the full blueprint in your output. The orchestrator attaches
  it automatically. Only emit the generated code fields: `pages`, `components`,
  `layout_source`, `global_css`, `design_tokens_applied`, `config_files`.
- Each item in `pages` MUST use these keys — not aliases:
    `slug` (e.g. "/", "/about", "/services/detailing"),
    `file_path` (NOT `path` / `filepath` / `file`),
    `source_code` (NOT `content` / `code`),
    `sections_used` (array of strings).
  Example:
    {
      "slug": "/about",
      "file_path": "app/about/page.tsx",
      "source_code": "export default function AboutPage() { ... }",
      "sections_used": ["hero", "team", "cta_band"]
    }
- Each item in `components` MUST use these keys — not aliases:
    `name` (e.g. "Hero", "Footer"),
    `file_path` (NOT `path`),
    `source_code` (NOT `content`).
  Example:
    {
      "name": "Hero",
      "file_path": "components/Hero.tsx",
      "source_code": "export function Hero() { ... }"
    }
- `design_tokens_applied` MUST be a FLAT object where every value is a SINGLE
  STRING — not a nested object. Collapse nested groups into one string using
  `"; "` between entries. Example:
    "design_tokens_applied": {
      "colors": "forge-black: #0F1117; signal-green: #00E87A",
      "typography": "heading: DM Sans (700); body: Inter (400)",
      "spacing": "section-padding-y-desktop: 96px; section-padding-x: 24px"
    }
  NOT: {"colors": {"forge-black": "#0F1117", ...}, ...}
- `config_files` MUST be a FLAT object mapping filename → file contents (string).
  Example: {"tailwind.config.ts": "import type ...", "next.config.js": "..."}
- Output must be a raw JSON object matching the schema — no wrapping in
  `properties`, no extra keys outside the schema."""


async def run(
    *,
    project: Project,
    inputs: dict[str, dict[str, Any]],
    on_progress: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = inputs.get(ArtifactType.NORMALIZED_INPUT, {})
    strategy = inputs.get(ArtifactType.STRATEGY, {})
    brand_identity = inputs.get(ArtifactType.BRAND_IDENTITY, {})

    website_type = (
        project.selected_website_type
        or project.recommended_website_type
        or "brochure_static"
    )

    # ── Phase 1: plan ────────────────────────────────────────────────────
    plan_user_prompt = f"""Create a website blueprint for this business.

Website type: {website_type}

Business profile:
{json.dumps(normalized, indent=2)}

Strategy (for positioning, tone, taglines, CTAs):
{json.dumps(strategy, indent=2)}

Brand identity (visual tokens — apply these to section notes where relevant):
{json.dumps(brand_identity, indent=2)}

Generate the complete blueprint with pages, sections, navigation, forms, and SEO strategy.
Set website_type to "{website_type}" in the output."""

    blueprint, plan_metadata = await generate_structured(
        system_prompt=PLAN_SYSTEM_PROMPT,
        user_prompt=plan_user_prompt,
        response_model=WebsiteBlueprint,
        model_tier="reasoning",
        temperature=0.3,
    )

    if not project.recommended_website_type:
        project.recommended_website_type = blueprint.website_type

    blueprint_payload = blueprint.model_dump(mode="json")

    # Publish the blueprint early so reviewers can see "what's planned"
    # while the code-gen phase (the slow one) is still running. The same
    # artifact row will be rewritten below with pages + components attached.
    if on_progress is not None:
        preview: dict[str, Any] = {
            "blueprint": blueprint_payload,
            "pages": [],
            "components": [],
            "design_tokens_applied": {},
            "config_files": {},
        }
        await on_progress(preview)

    # ── Phase 2: build ───────────────────────────────────────────────────
    build_user_prompt = f"""Generate a complete Next.js website from this blueprint and brand identity.

Website Blueprint:
{json.dumps(blueprint_payload, indent=2)}

Brand Identity (colors, typography, CTA styles, surfaces — apply these as design tokens):
{json.dumps(brand_identity, indent=2)}

Generate all pages, components, layout, and config files. Return structured output with
file paths and source code. Do NOT re-emit the blueprint; it will be attached automatically."""

    build, build_metadata = await generate_structured(
        system_prompt=BUILD_SYSTEM_PROMPT,
        user_prompt=build_user_prompt,
        response_model=WebsiteBuild,
        model_tier="builder",
        temperature=0.2,
    )

    # Attach the blueprint regardless of whether the model tried to echo it —
    # the orchestrator is the source of truth for what got planned.
    build.blueprint = blueprint

    metadata: dict[str, Any] = {"plan": plan_metadata, "build": build_metadata}
    return build.model_dump(mode="json"), metadata
