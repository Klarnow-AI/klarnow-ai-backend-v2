"""Brand identity artifact schema (merged).

Replaces the previous split between :mod:`app.schemas.identity` (text:
archetype, voice, taglines) and :mod:`app.schemas.design_system` (tokens:
colors, typography, CTAs). Voice-related text fields (``tone_of_voice``,
``voice_rules``, ``tagline_options``) now live on :class:`Strategy` because
they *power* visual generation rather than being visual deliverables.

The artifact this schema describes is visual: a palette, type system, and
(eventually) a rendered logo. Textual fields that remain here —
``brand_archetype``, ``visual_direction``, ``logo_direction`` — exist only
to feed the website builder and image generator, not as user-facing copy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _stringify_dict(data: dict[str, Any]) -> str:
    """Flatten a dict-of-scalars into a human-readable ``"key: value"`` string."""
    parts: list[str] = []
    for k, v in data.items():
        if v is None or v == "":
            continue
        if isinstance(v, list):
            text = ", ".join(str(x) for x in v if x not in (None, ""))
        elif isinstance(v, dict):
            text = ", ".join(
                f"{kk}: {vv}" for kk, vv in v.items() if vv not in (None, "")
            )
        else:
            text = str(v)
        if text:
            parts.append(f"{k}: {text}")
    return "; ".join(parts)


def _coerce_name_from_aliases(
    data: Any,
    primary: str,
    aliases: tuple[str, ...],
) -> Any:
    """Pull ``primary`` from any alias key if it's missing/blank."""
    if not isinstance(data, dict):
        return data
    d = dict(data)
    current = d.get(primary)
    if isinstance(current, str) and current.strip():
        return d
    for alt in aliases:
        val = d.get(alt)
        if isinstance(val, str) and val.strip():
            d[primary] = val.strip()
            return d
    return d


class ColorToken(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    hex: str
    usage: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:
        data = _coerce_name_from_aliases(data, "name", ("role", "label", "token"))
        if isinstance(data, dict):
            d = dict(data)
            h = d.get("hex")
            if not (isinstance(h, str) and h.strip()):
                for alt in ("value", "color", "hex_value", "hex_code"):
                    val = d.get(alt)
                    if isinstance(val, str) and val.strip():
                        d["hex"] = val.strip()
                        break
            return d
        return data


class TypographyToken(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str  # "heading" | "body" | "caption" | "mono"
    font_family: str
    weight: str | None = None
    size_class: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_font_family(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        ff = d.get("font_family")
        if isinstance(ff, str) and ff.strip():
            return d
        for alt in ("family", "font", "typeface", "font_name", "name"):
            val = d.get(alt)
            if isinstance(val, str) and val.strip():
                d["font_family"] = val.strip()
                return d
        return d


class CTAStyle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    variant: str
    background_color: str | None = None
    text_color: str | None = None
    border_radius: str | None = None
    label_style: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_variant(cls, data: Any) -> Any:
        return _coerce_name_from_aliases(
            data, "variant", ("name", "role", "type", "style", "kind")
        )


class SurfaceStyle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    background: str | None = None
    border: str | None = None
    shadow: str | None = None
    corner_radius: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_name(cls, data: Any) -> Any:
        return _coerce_name_from_aliases(
            data, "name", ("role", "surface", "type", "kind", "variant")
        )


class BrandIdentity(BaseModel):
    """Merged visual identity + design tokens artifact.

    Contains everything needed to render a brand on screen: colors,
    typography, CTA / surface treatments, and a textual ``logo_direction``
    that the (future) image agent will render into an actual PNG at
    ``logo_url``.
    """

    model_config = ConfigDict(extra="ignore")

    # Lightweight context for downstream agents (website_builder,
    # website_builder, image generator). Kept short — this isn't a
    # user-facing deliverable.
    brand_archetype: str | None = None
    visual_direction: str | None = None
    imagery_style: str | None = None  # e.g. "photography", "illustration", "abstract"
    icon_style: str | None = None  # e.g. "outlined", "filled", "duotone"
    logo_direction: str | None = None
    # Populated by a downstream image-generation step. Empty string until
    # then — NOT required for the agent to complete.
    logo_url: str = ""

    # Visual tokens — the actual output of this stage.
    color_palette: list[ColorToken] = Field(default_factory=list)
    typography: list[TypographyToken] = Field(default_factory=list)
    spacing_style: str | None = None
    corner_radius: str | None = None
    cta_styles: list[CTAStyle] = Field(default_factory=list)
    surface_styles: list[SurfaceStyle] = Field(default_factory=list)
    component_treatments: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_nullable_strings(cls, data: Any) -> Any:
        """Drop ``None`` for fields the LLM sometimes emits as null.

        ``logo_url`` in particular is declared as ``str = ""`` (empty until
        the image generator fills it), but models occasionally return
        ``logo_url: null`` which would otherwise raise a Pydantic
        ``string_type`` error and fail the whole stage. We treat null here
        as "not set yet" and let the default kick in.
        """
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if d.get("logo_url") is None:
            d.pop("logo_url", None)
        return d

    @model_validator(mode="before")
    @classmethod
    def _coerce_component_treatments(cls, data: Any) -> Any:
        """Flatten nested ``component_treatments`` into single-string values."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        treatments = d.get("component_treatments")
        if not isinstance(treatments, dict):
            return d
        coerced: dict[str, str] = {}
        for name, value in treatments.items():
            if isinstance(value, str):
                coerced[name] = value
            elif isinstance(value, dict):
                coerced[name] = _stringify_dict(value)
            elif isinstance(value, list):
                coerced[name] = ", ".join(
                    str(x) for x in value if x not in (None, "")
                )
            elif value is None:
                continue
            else:
                coerced[name] = str(value)
        d["component_treatments"] = coerced
        return d
