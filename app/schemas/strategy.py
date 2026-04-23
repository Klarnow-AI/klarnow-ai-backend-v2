"""Strategy artifact schema.

Produced by the StrategyAgent from the normalized business input.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KeyMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: str
    supporting_point: str = Field(
        default="",
        description="One concrete proof line, stat, or detail that backs the headline.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_supporting_point(cls, data: Any) -> Any:
        """LLMs often emit only ``headline`` or use alternate keys; normalize."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        sp = d.get("supporting_point")
        if isinstance(sp, str) and sp.strip():
            return d
        for alt in (
            "supporting_points",
            "support",
            "body",
            "proof",
            "detail",
            "subhead",
            "copy",
            "evidence",
            "rationale",
        ):
            val = d.get(alt)
            if isinstance(val, str) and val.strip():
                d["supporting_point"] = val.strip()
                return d
            if isinstance(val, list) and val:
                d["supporting_point"] = "; ".join(
                    str(x).strip() for x in val if str(x).strip()
                )
                return d
        d["supporting_point"] = ""
        return d


class Strategy(BaseModel):
    """Structured brand strategy artifact."""

    model_config = ConfigDict(extra="ignore")

    positioning_statement: str
    audience_summary: str
    core_values: list[str] = Field(default_factory=list)
    brand_voice: str | None = None
    key_messages: list[KeyMessage] = Field(default_factory=list)
    competitive_differentiation: str | None = None
    primary_cta: str | None = None
    elevator_pitch: str | None = None
    mission: str | None = None
    vision: str | None = None
    # Text that powers downstream visual generation. Moved here from the
    # old ``Identity`` schema when we merged identity + design_system into
    # a visual-first ``BrandIdentity`` stage.
    tagline_options: list[str] = Field(
        default_factory=list,
        description="3-5 short taglines the website/creative agents can pick from.",
    )
    voice_rules: list[str] = Field(
        default_factory=list,
        description="Short rules that constrain all downstream copy (e.g. 'never use emojis').",
    )
