"""Pipeline configuration — stage graph, model tiers, approval gates."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.enums import ArtifactType


@dataclass(frozen=True)
class StageDefinition:
    """Defines a single pipeline stage."""
    name: str
    artifact_type: str
    depends_on: tuple[str, ...] = ()
    approval_gate: bool = False
    model_tier: str = "default"


# Stage dependency graph per ARCHITECTURE.md
STAGES: tuple[StageDefinition, ...] = (
    StageDefinition(
        name="input_normalizer",
        artifact_type=ArtifactType.NORMALIZED_INPUT,
        depends_on=(),
        model_tier="fast",
    ),
    StageDefinition(
        name="strategy",
        artifact_type=ArtifactType.STRATEGY,
        depends_on=("input_normalizer",),
        approval_gate=True,
        model_tier="reasoning",
    ),
    StageDefinition(
        name="brand_identity",
        artifact_type=ArtifactType.BRAND_IDENTITY,
        depends_on=("strategy",),
        approval_gate=True,
        model_tier="creative",
    ),
    StageDefinition(
        name="website_builder",
        # The builder now owns planning: it runs a reasoning-tier blueprint
        # pass internally, then builds from it. Hence it takes the same three
        # upstream inputs the old planner did (profile + strategy + identity)
        # rather than depending on a separate planner stage. The approval gate
        # sits here — users review the built website, not a plan spec.
        artifact_type=ArtifactType.WEBSITE_BUILD,
        depends_on=("input_normalizer", "strategy", "brand_identity"),
        approval_gate=True,
        model_tier="builder",
    ),
    StageDefinition(
        name="creative_asset",
        artifact_type=ArtifactType.CREATIVE_CAMPAIGN,
        depends_on=("strategy", "brand_identity"),
        model_tier="creative",
    ),
    StageDefinition(
        name="qa",
        artifact_type=ArtifactType.QA_REPORT,
        depends_on=("website_builder", "creative_asset"),
        model_tier="fast",
    ),
)

STAGE_MAP: dict[str, StageDefinition] = {s.name: s for s in STAGES}

# Model tier → OpenRouter model slug mapping
MODEL_TIERS: dict[str, str] = {
    "fast": "openai/gpt-4o-mini",
    "default": "openai/gpt-4o",
    "reasoning": "anthropic/claude-sonnet-4-6",
    "creative": "anthropic/claude-sonnet-4-6",
    "builder": "anthropic/claude-opus-4-6",
}

PIPELINE_VERSION = "1"
