"""Website build artifact schema.

Produced by the WebsiteBuilderAgent. The builder now owns planning too: it
runs a blueprint pass internally and then generates the Next.js files in the
same stage, so this artifact ships the plan and the generated files together
instead of referencing a separate ``website_blueprint`` artifact.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.website_blueprint import WebsiteBlueprint


# ──────────────────────────────────────────────────────────────────────────
# Coercion helpers
# ──────────────────────────────────────────────────────────────────────────


def _pick_first_str(d: dict, keys: tuple[str, ...]) -> str | None:
    """Return the first populated string value among ``keys`` (case-sensitive)."""
    for key in keys:
        val = d.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _slug_from_file_path(file_path: str) -> str:
    """Best-effort slug inference for Next.js App Router paths.

    ``app/page.tsx`` → ``/``
    ``app/about/page.tsx`` → ``/about``
    ``app/services/detailing/page.tsx`` → ``/services/detailing``
    ``app/not-found.tsx`` → ``/404``
    Anything else falls back to the file basename minus extension.
    """
    if not file_path:
        return ""
    cleaned = file_path.strip().lstrip("/")
    # Strip leading "app/" — conventional for App Router.
    if cleaned.startswith("app/"):
        cleaned = cleaned[len("app/"):]
    # ``app/page.tsx`` → ``""`` → "/"
    if cleaned in {"page.tsx", "page.jsx", "page.ts", "page.js"}:
        return "/"
    # ``foo/bar/page.tsx`` → "/foo/bar"
    m = re.match(r"^(.*)/page\.(tsx|jsx|ts|js)$", cleaned)
    if m:
        return "/" + m.group(1)
    # ``not-found.tsx`` → "/404"
    if cleaned.startswith("not-found."):
        return "/404"
    # Fallback: filename without extension.
    stem = re.sub(r"\.(tsx|jsx|ts|js)$", "", cleaned)
    return "/" + stem if not stem.startswith("/") else stem


def _name_from_file_path(file_path: str) -> str:
    """Best-effort component name from its file path.

    ``components/Hero.tsx`` → ``Hero``. Falls back to the raw stem.
    """
    if not file_path:
        return ""
    stem = file_path.strip().split("/")[-1]
    return re.sub(r"\.(tsx|jsx|ts|js)$", "", stem)


def _stringify_tokens(value: Any) -> str:
    """Flatten an arbitrary token value to a compact, readable string.

    ``{"primary": "#0F1117", "accent": "#00E87A"}``
      → ``"primary: #0F1117; accent: #00E87A"``
    ``["bg-signal-green", "hover:bg-lime"]``
      → ``"bg-signal-green, hover:bg-lime"``
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts: list[str] = []
        for k, v in value.items():
            if v in (None, ""):
                continue
            parts.append(f"{k}: {_stringify_tokens(v)}")
        return "; ".join(parts)
    if isinstance(value, list):
        return ", ".join(
            _stringify_tokens(item) for item in value if item not in (None, "")
        )
    if value is None:
        return ""
    return str(value)


# ──────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────


class GeneratedPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    file_path: str  # e.g. "app/page.tsx", "app/about/page.tsx"
    source_code: str
    sections_used: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        """LLMs routinely output ``path`` / ``content`` / ``code`` instead of the
        canonical keys, and forget ``slug`` altogether. Fill in whatever we can
        before Pydantic sees it so validation stops failing on 15+ identical
        alias mismatches."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        # file_path ← path / filepath / file
        if not (isinstance(d.get("file_path"), str) and d["file_path"].strip()):
            alt = _pick_first_str(d, ("path", "filepath", "file", "filename"))
            if alt:
                d["file_path"] = alt
        # source_code ← content / code / source / body
        if not (isinstance(d.get("source_code"), str) and d["source_code"].strip()):
            alt = _pick_first_str(d, ("content", "code", "source", "body", "text"))
            if alt:
                d["source_code"] = alt
        # slug ← route / href / url, else inferred from file_path
        if not (isinstance(d.get("slug"), str) and d["slug"].strip()):
            alt = _pick_first_str(d, ("route", "href", "url", "path_slug", "page_slug"))
            if alt:
                d["slug"] = alt
            elif isinstance(d.get("file_path"), str):
                d["slug"] = _slug_from_file_path(d["file_path"])
        return d


class GeneratedComponent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    file_path: str  # e.g. "components/Hero.tsx"
    source_code: str

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        """Mirror of :class:`GeneratedPage`'s coercion. ``name`` defaults to the
        file's basename (``components/Hero.tsx`` → ``Hero``) when the LLM omits
        it."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if not (isinstance(d.get("file_path"), str) and d["file_path"].strip()):
            alt = _pick_first_str(d, ("path", "filepath", "file", "filename"))
            if alt:
                d["file_path"] = alt
        if not (isinstance(d.get("source_code"), str) and d["source_code"].strip()):
            alt = _pick_first_str(d, ("content", "code", "source", "body", "text"))
            if alt:
                d["source_code"] = alt
        if not (isinstance(d.get("name"), str) and d["name"].strip()):
            alt = _pick_first_str(d, ("component_name", "label", "title"))
            if alt:
                d["name"] = alt
            elif isinstance(d.get("file_path"), str):
                inferred = _name_from_file_path(d["file_path"])
                if inferred:
                    d["name"] = inferred
        return d


class WebsiteBuild(BaseModel):
    """Generated Next.js website artifact.

    ``blueprint`` is the internal plan the builder produced in its first pass
    before writing code. It's kept alongside the generated files so reviewers
    can see *what was planned* and *what was built* in one artifact, and so
    downstream agents don't need to juggle two separate inputs.
    """

    model_config = ConfigDict(extra="ignore")

    blueprint: WebsiteBlueprint | None = None
    pages: list[GeneratedPage] = Field(default_factory=list)
    components: list[GeneratedComponent] = Field(default_factory=list)
    layout_source: str | None = None  # root layout.tsx
    global_css: str | None = None  # globals.css / tailwind config
    design_tokens_applied: dict[str, str] = Field(default_factory=dict)
    config_files: dict[str, str] = Field(default_factory=dict)  # e.g. next.config.js, tailwind.config.ts
    bundle_file_id: str | None = None  # PocketBase file reference for downloadable zip

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        """Flatten nested dicts in ``design_tokens_applied`` / ``config_files``.

        The LLM likes to return ``{"colors": {"primary": "#000"}, ...}`` even
        when the schema declares ``dict[str, str]``. Collapse each nested value
        to a single compact string so the structural information survives
        validation instead of blowing up 5+ string_type errors."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        for key in ("design_tokens_applied", "config_files"):
            val = d.get(key)
            if not isinstance(val, dict):
                continue
            coerced: dict[str, str] = {}
            for k, v in val.items():
                if v in (None, ""):
                    continue
                coerced[str(k)] = _stringify_tokens(v)
            d[key] = coerced
        return d
