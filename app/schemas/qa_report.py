"""QA report artifact schema.

Produced by the QAAgent after all generation stages complete.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QACheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_name: str
    category: str  # tone_consistency, message_consistency, audience_consistency, factual_grounding, completeness, cta_clarity
    status: Literal["passed", "warning", "failed"]
    detail: str | None = None
    affected_artifact: str | None = None  # artifact_type that has the issue


class QAIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    severity: Literal["low", "medium", "high"]
    description: str
    affected_artifact: str | None = None
    suggested_fix: str | None = None


class QAReport(BaseModel):
    """Structured QA review artifact."""

    model_config = ConfigDict(extra="ignore")

    overall_status: Literal["passed", "warning", "failed"] = "passed"
    consistency_score: int = Field(default=100, ge=0, le=100)
    checks: list[QACheck] = Field(default_factory=list)
    issues: list[QAIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    artifact_versions_reviewed: dict[str, int] = Field(default_factory=dict)
