# Onboarding Multi-Agent Pipeline Plan

Status: Proposed fallback architecture plan
Date: 2026-03-25
Scope: Pack onboarding background pipeline and downstream business growth asset generation

## Purpose

This document captures the current onboarding flow, the target multi-agent flow, the artifact contracts between stages, and the recommended rollout path.

Use this as the fallback reference if implementation discussions drift or if we need to realign on what "the architecture" means in practical repo terms.

## Current State

Today the onboarding system is a deterministic staged worker, not yet a full typed multi-agent handoff pipeline.

Current worker flow:

`brand_os -> starter_brand -> logo -> website -> poster_flyers -> videos`

Current existing-brand flow:

`brand_os -> website -> poster_flyers -> videos`

Notes:

- The worker orchestration already exists in `app/modules/packs/onboarding/runner.py`.
- Stage names and public grouping already exist in `app/modules/packs/onboarding/constants.py`.
- Brand extraction already exists in `app/modules/packs/onboarding_services.py`.
- Brand OS generation already exists in `app/modules/brand_os/tools.py`.
- Shared downstream context assembly already exists in `app/shared/services/generation_context.py`.

Current strengths:

- deterministic orchestration
- durable background execution with retries and pause/resume
- Brand OS is already a first-class strategic artifact
- website and creative generation already reuse shared brand context

Current gaps relative to the target architecture:

- no dedicated `normalize_input` stage
- no canonical `NormalizedBusinessProfile` artifact
- brand identity is split across `starter_brand` and `logo`
- downstream stages still depend partly on raw pack fields or onboarding answers
- no final cross-output QA stage

## Target Flow

Near-term implementation target:

`normalize_input -> brand_os -> brand_identity -> website -> poster_flyers -> videos -> qa_review`

Longer-term extension:

`normalize_input -> brand_os -> brand_identity -> website_blueprint -> creative_bundle -> video_briefs -> video_render -> qa_review`

Core rule:

Each stage should read typed artifacts from upstream stages, not raw `pack.onboarding_answers`, except where the normalization stage is intentionally ingesting raw inputs.

## Architectural Principles

- Schema first: each stage produces a validated artifact with an explicit contract.
- Deterministic orchestration: the worker controls ordering, retries, skips, pause/resume, and completion rules.
- Functional stage boundaries: each stage performs one bounded transformation.
- Shared strategic memory: Brand OS and brand identity become the source of truth for downstream generation.
- QA as a gate: the run ends with a coherence check across all generated outputs.
- Agentic behavior stays inside stage implementations: the orchestrator is a controller, not a free-form reasoning agent.

## Proposed Artifacts

### 1. `NormalizedBusinessProfile`

Produced by: `normalize_input`

Purpose: standardize messy business input into a clean business context for all downstream stages.

Suggested fields:

- `business_name`
- `industry`
- `target_audience`
- `core_offer`
- `problem_solved`
- `differentiators`
- `goals`
- `tone_preferences`
- `geographic_focus`
- `competitor_signals`
- `constraints`
- `available_channels`
- `source_evidence`
- `missing_fields`

### 2. `BrandOS`

Produced by: `brand_os`

Purpose: strategic source of truth for positioning, messaging, audience, and CTA direction.

Suggested fields:

- `brand_purpose`
- `audience_personas`
- `positioning_statement`
- `one_line_offer`
- `value_proposition`
- `messaging_pillars`
- `proof_points`
- `tone_attributes`
- `cta_framework`
- `strategic_summary`

### 3. `BrandIdentityProfile`

Produced by: `brand_identity`

Purpose: translate strategy into visual and verbal identity rules.

Suggested fields:

- `personality_traits`
- `visual_keywords`
- `palette_direction`
- `typography_direction`
- `logo_direction`
- `image_style`
- `voice_rules`
- `design_dos`
- `design_donts`
- `tagline_options`

### 4. `WebsiteBlueprint`

Produced by: `website`

Purpose: express Brand OS and identity as a conversion-focused website structure and copy system.

Suggested fields:

- `page_list`
- `page_goals`
- `section_hierarchy`
- `copy_blocks`
- `trust_elements`
- `faq`
- `cta_map`
- `funnel_logic`

### 5. `CreativeBriefBundle`

Produced by: `poster_flyers`

Purpose: produce campaign-ready poster and flyer creative aligned with strategy and identity.

Suggested fields:

- `campaign_objective`
- `asset_audience`
- `headline_options`
- `support_copy`
- `cta`
- `design_briefs`
- `visual_prompts`
- `format_variants`

### 6. `VideoBriefBundle`

Produced by: `videos`

Purpose: produce video concepts, scripts, and render-ready direction aligned with the same strategic foundation.

Suggested fields:

- `concept_summary`
- `hook`
- `storyboard`
- `voiceover_script`
- `captions`
- `end_frame_cta`
- `render_prompts`

### 7. `QAReport`

Produced by: `qa_review`

Purpose: verify consistency and quality across all stage outputs before the onboarding run is considered complete.

Suggested fields:

- `overall_status`
- `consistency_score`
- `passed_checks`
- `failed_checks`
- `repair_actions`
- `artifact_versions`

## Stage Responsibilities

### Normalization Agent

Transforms raw onboarding answers, extracted website/logo/paste context, and resolved pack fields into a clean `NormalizedBusinessProfile`.

It should:

- extract important business facts
- remove noise and duplication
- resolve obvious contradictions where possible
- identify missing critical fields
- preserve evidence for important assumptions

It should not:

- invent strategy
- generate brand identity
- generate assets

### Strategy Agent

Consumes `NormalizedBusinessProfile` and generates `BrandOS`.

It should:

- define audience
- define positioning
- define value proposition
- define messaging pillars
- define tone and CTA direction

It should not generate websites, posters, or videos.

### Brand Identity Agent

Consumes `BrandOS` and generates `BrandIdentityProfile`.

It should:

- define how the strategy should look and feel
- specify palette, typography, logo direction, and voice rules
- stay derived from strategy rather than inventing new positioning

Near term, this can wrap the current `starter_brand` and `logo` stages under one public identity artifact.

### Website Agent

Consumes `NormalizedBusinessProfile`, `BrandOS`, and `BrandIdentityProfile` to produce `WebsiteBlueprint` and downstream website assets.

It should focus on:

- information hierarchy
- conversion logic
- section-by-section copy
- CTA placement

### Poster/Flyer Agent

Consumes the same strategic and identity artifacts to generate `CreativeBriefBundle`.

It should focus on:

- campaign angle
- promotional headline and supporting copy
- visual composition direction
- CTA consistency

### Video Agent

Consumes the same strategic and identity artifacts to generate `VideoBriefBundle`.

It should focus on:

- concept angle
- hooks
- scene flow
- script and captions
- end-frame CTA

Near term, the existing onboarding video stage can remain, but the target model is "brief/script first, render second."

### QA / Consistency Agent

Consumes all generated artifacts and produces `QAReport`.

It should validate:

- same target audience
- same offer and value proposition
- same CTA direction
- same tone and voice
- same proof logic
- same visual identity cues
- same positioning across website, creative, and video outputs

### Orchestrator

The orchestrator remains the control layer rather than a content generator.

It should manage:

- execution order
- skip rules
- retries
- pause/resume
- artifact passing
- validation thresholds
- completion rules

## Repo Mapping

Current files to extend:

- `app/modules/packs/onboarding/constants.py`
- `app/modules/packs/onboarding/runner.py`
- `app/modules/packs/onboarding_jobs.py`
- `app/modules/packs/onboarding/stages/brand_os.py`
- `app/modules/packs/onboarding/stages/starter_brand.py`
- `app/modules/packs/onboarding/stages/logo.py`
- `app/modules/packs/onboarding/stages/website.py`
- `app/modules/packs/onboarding/stages/poster_flyers.py`
- `app/modules/packs/onboarding/stages/videos.py`
- `app/modules/packs/onboarding_services.py`
- `app/modules/packs/services.py`
- `app/modules/packs/tools.py`
- `app/shared/services/generation_context.py`
- `app/modules/agents/register_tools.py`
- `app/modules/ad_factory/services.py`

Recommended new files:

- `app/modules/packs/onboarding/stages/normalize_input.py`
- `app/modules/packs/onboarding/stages/qa_review.py`
- `app/modules/packs/onboarding/artifacts.py`
- `app/modules/packs/onboarding/artifact_store.py`

## Rollout Plan

### Phase 1: Add the missing architecture pieces without replacing the worker

Goals:

- add artifact schemas
- add `normalize_input`
- add `qa_review`
- keep the current worker and most stage internals intact

Changes:

- extend stage constants and worker ordering
- persist `NormalizedBusinessProfile`
- persist `QAReport`
- keep current website, poster, and video generation behavior mostly unchanged

Success criteria:

- every onboarding run starts with normalized input
- every onboarding run ends with a QA result
- current generation outputs still work
- public stage reporting remains stable

### Phase 2: Make downstream generation artifact-driven

Goals:

- refactor downstream stages to read typed artifacts first
- reduce direct dependence on raw onboarding answers
- unify identity behavior behind one public artifact

Changes:

- refactor `generation_context.py` to resolve from artifacts first
- make website, poster, and video stages consume `BrandOS` and `BrandIdentityProfile`
- merge `starter_brand` and `logo` into a `brand_identity` artifact layer, even if the implementation remains internally split during transition

Success criteria:

- downstream stages use the same canonical strategic context
- the same audience, CTA, and voice are visible across generated outputs

### Phase 3: Add richer regeneration and agent exposure

Goals:

- expose stage capabilities as explicit tools
- support more targeted regeneration
- improve lineage and validation visibility

Changes:

- expand `register_tools.py` with pipeline-stage tools
- split video into `video_briefs` and `video_render` when ready
- allow bounded reruns after QA failure without recomputing everything

Success criteria:

- stage-level regeneration works cleanly
- artifact lineage is visible
- QA can drive selective repair rather than full pipeline reruns

## QA Checks for the Final Stage

The final QA stage should check at least:

- audience consistency
- offer and value proposition consistency
- CTA consistency
- tone and voice alignment
- proof and claims alignment
- palette, logo, and visual direction alignment
- website-to-creative message alignment
- video-to-strategy alignment
- missing required artifacts

## Non-Goals for the First Implementation

- building a free-form autonomous swarm
- dynamic stage ordering based on open-ended agent negotiation
- self-correcting loops across every stage
- dedicated database tables for every artifact on day one
- a production-grade video rendering rewrite

## Working Decisions

- Artifact storage can start cheap in onboarding job data or a pack-scoped artifact JSON layer before moving to dedicated tables.
- Existing-brand skip rules can remain, but `normalize_input` should run for both new and existing brands.
- Public stage reporting can expose a single `brand_identity` stage even if it still maps internally to `starter_brand` and `logo` during transition.
- QA should begin as a warning-plus-blocker system, where only major misalignment blocks completion at first.

## Definition of Done

We can call this architecture implemented when all of the following are true:

1. onboarding begins with a persisted `NormalizedBusinessProfile`
2. Brand OS consumes that artifact directly
3. brand identity, website, creative, and video stages all read typed artifacts instead of raw onboarding answers as their primary source
4. every onboarding run produces a `QAReport`
5. the orchestrator can show stage status and artifact lineage clearly

## Short Version

Current implemented flow:

`brand_os -> starter_brand -> logo -> website -> poster_flyers -> videos`

Target implementation flow:

`normalize_input -> brand_os -> brand_identity -> website -> poster_flyers -> videos -> qa_review`

Safest first step:

Add `normalize_input` and `qa_review` on top of the current worker, then progressively refactor downstream stages to consume typed artifacts.
