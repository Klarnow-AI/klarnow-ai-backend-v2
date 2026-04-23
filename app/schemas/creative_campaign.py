"""Creative campaign artifact schema.

Produced by :mod:`app.modules.pipeline.agents.creative_asset`. The agent
works in two phases — a copywriter phase (LLM generates concept + per-asset
copy specs) and a designer phase (a second LLM pass turns each spec into a
self-contained React/JSX component using brand design tokens). We ship code,
not rasters — posters, flyers, and social posts all render as JSX on the
frontend inside a sandboxed iframe. Rasterization (for actual social uploads)
is a later, optional step.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetSpec(BaseModel):
    """Specification for a single creative asset (poster, flyer, social post).

    Phase-1 copywriter output fills ``headline`` / ``body_copy`` / ``cta_text``
    / ``layout_notes``. Phase-2 designer fills ``jsx_code`` with a self-
    contained React component source (no imports, no Tailwind, inline styles
    using brand hex values and fonts) that the frontend renders inside a
    sandboxed iframe at exactly ``width_px`` x ``height_px``.

    ``jsx_code`` stays empty if design generation fails — the copy spec is
    still useful on its own and can be re-rendered later.
    """

    model_config = ConfigDict(extra="ignore")

    # Stable id per spec — used by the frontend to match the optimistic
    # "imagining…" tile a user just submitted to the populated spec streamed
    # back from the server. We default to a fresh uuid4 hex if the LLM (or an
    # older artifact payload) doesn't carry one.
    id: str = Field(default_factory=lambda: uuid4().hex)
    asset_type: str  # poster, flyer, social_instagram, social_linkedin, social_facebook
    format: str  # e.g. "4x5", "1x1", "16x9", "A4"
    headline: str
    body_copy: str | None = None
    cta_text: str | None = None
    layout_notes: str | None = None
    design_token_overrides: dict[str, str] = Field(default_factory=dict)
    # Lifecycle marker surfaced to the UI so pending tiles show a shimmer
    # instead of "render unavailable" while the designer is still writing
    # the JSX. "pending" is the on-demand flow; the pipeline's own assets
    # land straight in "ok" or "error" based on the designer outcome.
    status: str = "ok"  # "pending" | "ok" | "error"
    # JSX source for a React functional component. Must be runnable in a
    # sandboxed iframe after an in-browser Babel transform: no imports, no
    # external CSS, all styles inline. Empty until phase-2 renders it.
    jsx_code: str = ""
    # Target viewport the JSX expects to render inside. Set by the agent from
    # the format field so the iframe can scale the asset without distorting
    # type.
    width_px: int = 1080
    height_px: int = 1080

    @model_validator(mode="before")
    @classmethod
    def _coerce_nullable_strings(cls, data: Any) -> Any:
        # The copywriter LLM often emits ``"jsx_code": null`` (and historically
        # ``"image_url": null``) for each spec because design generation is a
        # downstream step. Pydantic's ``str`` type rejects ``None`` outright,
        # so we drop those keys and let the defaults stand in. Same deal for
        # ``id`` and ``status`` on older payloads that predate these fields.
        if not isinstance(data, dict):
            return data
        for nullable_str_key in ("jsx_code", "image_url", "id", "status"):
            if data.get(nullable_str_key) is None:
                data = {**data}
                data.pop(nullable_str_key, None)
        return data


class CreativeCampaign(BaseModel):
    """Structured creative campaign artifact."""

    model_config = ConfigDict(extra="ignore")

    campaign_concept: str
    campaign_headline: str
    poster_copy: str | None = None
    flyer_copy: str | None = None
    social_captions: list[str] = Field(default_factory=list)
    email_subject_lines: list[str] = Field(default_factory=list)
    promotional_hook: str | None = None
    asset_specs: list[AssetSpec] = Field(default_factory=list)
