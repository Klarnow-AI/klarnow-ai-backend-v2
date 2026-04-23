"""QA report artifact schema.

Produced by the QAAgent after all generation stages complete.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ──────────────────────────────────────────────────────────────────────────
# Coercion helpers
# ──────────────────────────────────────────────────────────────────────────


# Map common LLM severity synonyms to our canonical values so the enum stays
# small while accepting the noisy real-world outputs models emit.
_SEVERITY_ALIASES: dict[str, str] = {
    "warning": "medium",
    "warn": "medium",
    "moderate": "medium",
    "med": "medium",
    "info": "low",
    "informational": "low",
    "notice": "low",
    "note": "low",
    "minor": "low",
    "trivial": "low",
    "error": "high",
    "critical": "high",
    "severe": "high",
    "fail": "high",
    "failed": "high",
    "blocker": "high",
    "major": "high",
}


def _coerce_artifact_list(value: Any) -> list[str]:
    """Normalise ``affected_artifact`` input to a ``list[str]``.

    Accepts the three shapes LLMs commonly emit — ``None``, a single string, or
    a list — and returns a clean list with empty entries stripped."""
    if value in (None, ""):
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if item in (None, ""):
                continue
            out.append(str(item).strip())
        return [x for x in out if x]
    return [str(value).strip()]


def _coerce_severity(value: Any) -> Any:
    """Map ``warning`` / ``error`` / ``info`` and friends onto ``low``/``medium``/``high``.

    Anything already valid (or unknown) is returned unchanged so Pydantic can
    still fail loudly on truly novel values instead of masking them."""
    if not isinstance(value, str):
        return value
    cleaned = value.strip().lower()
    if cleaned in {"low", "medium", "high"}:
        return cleaned
    return _SEVERITY_ALIASES.get(cleaned, value)


# ──────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────


class QACheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_name: str
    category: str  # tone_consistency, message_consistency, audience_consistency, factual_grounding, completeness, cta_clarity
    status: Literal["passed", "warning", "failed"]
    detail: str | None = None
    # A single check can implicate multiple artifacts (e.g. tone drift between
    # website copy *and* campaign copy). Accept any of None / str / list[str]
    # in the input and normalise to a list.
    affected_artifact: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "affected_artifact" in d:
            d["affected_artifact"] = _coerce_artifact_list(d["affected_artifact"])
        return d


class QAIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    severity: Literal["low", "medium", "high"]
    description: str
    affected_artifact: list[str] = Field(default_factory=list)
    suggested_fix: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if "severity" in d:
            d["severity"] = _coerce_severity(d["severity"])
        if "affected_artifact" in d:
            d["affected_artifact"] = _coerce_artifact_list(d["affected_artifact"])
        return d


class QAReport(BaseModel):
    """Structured QA review artifact."""

    model_config = ConfigDict(extra="ignore")

    overall_status: Literal["passed", "warning", "failed"] = "passed"
    consistency_score: int = Field(default=100, ge=0, le=100)
    checks: list[QACheck] = Field(default_factory=list)
    issues: list[QAIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    artifact_versions_reviewed: dict[str, int] = Field(default_factory=dict)
