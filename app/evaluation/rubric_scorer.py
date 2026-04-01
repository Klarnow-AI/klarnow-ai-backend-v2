"""
Manual rubric scoring interface.

Provides a simple structure for recording human (examiner/researcher)
rubric scores alongside automated NLP metrics, enabling mixed-method
evaluation as described in the dissertation methodology.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RubricDimension(BaseModel):
    dimension: str
    score: float = Field(ge=0.0, le=5.0, description="0–5 scale")
    notes: str = ""


class RubricScore(BaseModel):
    scenario_id: str
    variant: str  # 'baseline' or 'grounded'
    output_type: str  # 'brand_os', 'identity', 'website', 'creative'
    dimensions: list[RubricDimension] = Field(default_factory=list)

    def average_score(self) -> float:
        if not self.dimensions:
            return 0.0
        return round(sum(d.score for d in self.dimensions) / len(self.dimensions), 3)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "variant": self.variant,
            "output_type": self.output_type,
            "average_score": self.average_score(),
            "dimensions": [d.model_dump() for d in self.dimensions],
        }


STANDARD_DIMENSIONS = [
    "Relevance to business context",
    "Brand consistency (tone and message)",
    "Specificity (concrete over generic)",
    "Actionability (useful to the business)",
    "Professional quality of language",
]


def empty_rubric(scenario_id: str, variant: str, output_type: str) -> RubricScore:
    """Return an empty rubric ready for manual scoring."""
    return RubricScore(
        scenario_id=scenario_id,
        variant=variant,
        output_type=output_type,
        dimensions=[
            RubricDimension(dimension=dim, score=0.0)
            for dim in STANDARD_DIMENSIONS
        ],
    )
