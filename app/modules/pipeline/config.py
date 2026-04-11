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
        name="identity",
        artifact_type=ArtifactType.IDENTITY,
        depends_on=("strategy",),
        approval_gate=True,
        model_tier="creative",
    ),
    StageDefinition(
        name="design_system",
        artifact_type=ArtifactType.DESIGN_SYSTEM,
        depends_on=("identity",),
        model_tier="creative",
    ),
    StageDefinition(
        name="website_planner",
        artifact_type=ArtifactType.WEBSITE_BLUEPRINT,
        depends_on=("design_system",),
        approval_gate=True,
        model_tier="reasoning",
    ),
    StageDefinition(
        name="website_builder",
        artifact_type=ArtifactType.WEBSITE_BUILD,
        depends_on=("website_planner",),
        model_tier="builder",
    ),
    StageDefinition(
        name="creative_asset",
        artifact_type=ArtifactType.CREATIVE_CAMPAIGN,
        depends_on=("design_system",),
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
