"""Website blueprint schema.

Produced internally by :mod:`app.modules.pipeline.agents.website_builder`
during its planning phase. This is no longer a standalone pipeline artifact
— it lives embedded on :class:`app.schemas.website_build.WebsiteBuild.blueprint`
so reviewers can see the plan alongside the generated files.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _cta_to_string(value: Any) -> str | None:
    """Flatten a CTA dict into a readable ``"Label → href (variant)"`` string.

    The LLM insists on returning ``{"label": ..., "href": ..., "variant": ...}``
    even when we ask for a string. This preserves every field we care about
    without dropping information on the floor.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, dict):
        label = value.get("label") or value.get("text") or value.get("title") or ""
        href = (
            value.get("href")
            or value.get("url")
            or value.get("link")
            or value.get("target")
            or value.get("slug")
            or ""
        )
        variant = value.get("variant") or value.get("style") or value.get("type") or ""
        label_str = str(label).strip()
        href_str = str(href).strip()
        variant_str = str(variant).strip()
        parts: list[str] = []
        if label_str:
            parts.append(label_str)
        if href_str:
            parts.append(f"→ {href_str}")
        if variant_str:
            parts.append(f"({variant_str})")
        rendered = " ".join(parts).strip()
        return rendered or None
    if isinstance(value, list):
        # Multiple CTAs on a section — join with `; `.
        rendered_list = [s for s in (_cta_to_string(v) for v in value) if s]
        return "; ".join(rendered_list) if rendered_list else None
    return str(value)


def _form_field_to_string(value: Any) -> str | None:
    """Flatten a form field descriptor dict into a single string.

    LLMs return rich objects (``{"name", "type", "required", "validation"}``)
    even when we declare ``fields: list[str]``. We render them as
    ``"name (type, required): validation"`` so all metadata survives.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name") or value.get("id") or value.get("label") or ""
        ftype = value.get("type") or value.get("field_type") or value.get("kind") or ""
        required = value.get("required")
        validation = (
            value.get("validation")
            or value.get("rules")
            or value.get("constraint")
            or ""
        )
        placeholder = value.get("placeholder") or value.get("help_text") or ""
        head_parts: list[str] = []
        if name:
            head_parts.append(str(name).strip())
        qualifier_parts: list[str] = []
        if ftype:
            qualifier_parts.append(str(ftype).strip())
        if required is True:
            qualifier_parts.append("required")
        elif required is False:
            qualifier_parts.append("optional")
        head = " ".join(head_parts)
        if qualifier_parts:
            head = f"{head} ({', '.join(qualifier_parts)})" if head else f"({', '.join(qualifier_parts)})"
        tail_parts: list[str] = []
        if isinstance(validation, str) and validation.strip():
            tail_parts.append(validation.strip())
        elif isinstance(validation, list) and validation:
            tail_parts.append(", ".join(str(v) for v in validation if v))
        if placeholder:
            tail_parts.append(f"placeholder: {str(placeholder).strip()}")
        rendered = head
        if tail_parts:
            rendered = f"{rendered}: {' — '.join(tail_parts)}" if rendered else " — ".join(tail_parts)
        return rendered.strip() or None
    return str(value)


class PageSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    section_type: str  # e.g. "hero", "features", "testimonials", "cta", "faq"
    purpose: str | None = None
    content_notes: str | None = None
    cta: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        # ``cta`` is commonly returned as {label, href, variant} — flatten.
        if "cta" in d and not isinstance(d["cta"], str):
            d["cta"] = _cta_to_string(d["cta"])
        # ``section_type`` sometimes arrives as ``type`` or ``name``.
        st = d.get("section_type")
        if not (isinstance(st, str) and st.strip()):
            for alt in ("type", "kind", "name", "role"):
                val = d.get(alt)
                if isinstance(val, str) and val.strip():
                    d["section_type"] = val.strip()
                    break
        return d


class PageDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str  # e.g. "home", "about", "services", "contact"
    title: str
    goal: str | None = None
    sections: list[PageSection] = Field(default_factory=list)
    seo_title: str | None = None
    seo_description: str | None = None


class NavigationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    href: str
    children: list[NavigationItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_href(cls, data: Any) -> Any:
        """LLMs often emit ``slug``/``url``/``path``/``link`` instead of
        ``href``. Canonicalise so navigation always has a target."""
        if not isinstance(data, dict):
            return data
        d = dict(data)
        href = d.get("href")
        if isinstance(href, str) and href.strip():
            return d
        for alt in ("slug", "url", "path", "link", "to", "target"):
            val = d.get(alt)
            if isinstance(val, str) and val.strip():
                d["href"] = val.strip()
                return d
        return d


class FormDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    purpose: str
    fields: list[str] = Field(default_factory=list)
    submit_action: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        # ``name`` often shows up as ``form_id``/``id``/``title``/``slug``.
        name = d.get("name")
        if not (isinstance(name, str) and name.strip()):
            for alt in ("form_id", "id", "slug", "title", "label", "form_name"):
                val = d.get(alt)
                if isinstance(val, str) and val.strip():
                    d["name"] = val.strip()
                    break
        # ``purpose`` might be named ``goal``/``description`` instead.
        purpose = d.get("purpose")
        if not (isinstance(purpose, str) and purpose.strip()):
            for alt in ("goal", "description", "intent", "summary"):
                val = d.get(alt)
                if isinstance(val, str) and val.strip():
                    d["purpose"] = val.strip()
                    break
        # Flatten field descriptor dicts into strings.
        fields = d.get("fields")
        if isinstance(fields, list):
            coerced: list[str] = []
            for item in fields:
                rendered = _form_field_to_string(item)
                if rendered:
                    coerced.append(rendered)
            d["fields"] = coerced
        return d


class WebsiteBlueprint(BaseModel):
    """Structured website blueprint artifact."""

    model_config = ConfigDict(extra="ignore")

    website_type: str  # landing_page, brochure_static, service_lead_gen
    primary_goal: str
    secondary_goals: list[str] = Field(default_factory=list)
    navigation: list[NavigationItem] = Field(default_factory=list)
    site_map: list[str] = Field(default_factory=list)
    pages: list[PageDefinition] = Field(default_factory=list)
    global_components: list[str] = Field(default_factory=list)
    forms: list[FormDefinition] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    seo_strategy: str | None = None
    design_application_notes: str | None = None
    cta_strategy: str | None = None
