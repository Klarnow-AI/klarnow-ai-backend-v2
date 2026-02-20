"""Governance: one CTA, no revenue guarantees, lock enforcement, proof-before-launch."""

import re

from app.core.errors import AppError

# Phrases that imply revenue guarantees (blocked in copy)
REVENUE_GUARANTEE_PATTERNS = [
    r"\bguarantee\s+(we\s+)?(you\s+)?(will\s+)?(make|earn|get)\b",
    r"\b(will\s+)?(make|earn|get)\s+you\s+\$",
    r"\b(will\s+)?(make|earn)\s+(you\s+)?\d+\s*%\s*(profit|return|revenue)\b",
    r"\bguaranteed\s+(results|income|revenue|profit)\b",
    r"\b(100\s*%|100%)\s*(guarantee|money\s+back)\b",
]


def validate_one_cta(primary_cta: str | None, angles: list | None = None) -> None:
    """Ensure campaign has exactly one primary CTA. Raise if invalid."""
    if not primary_cta or not str(primary_cta).strip():
        raise AppError("Campaign must have exactly one primary CTA", status_code=400)
    # Optional: ensure angles don't introduce extra CTAs in copy (Phase 2+)
    if angles is not None and not isinstance(angles, list):
        raise AppError("Angles must be a list", status_code=400)


def validate_no_revenue_guarantees(text: str) -> None:
    """Ensure copy does not promise revenue guarantees. Raise if invalid."""
    if not text or not str(text).strip():
        return
    lower = text.lower()
    for pattern in REVENUE_GUARANTEE_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            raise AppError(
                "Copy must not promise or guarantee revenue, income, or profit. Remove guarantee language.",
                status_code=400,
            )


def validate_conversion_page_cta(structure: dict | list | None, primary_cta: str | None) -> None:
    """Ensure conversion page structure has exactly one CTA that matches campaign.primary_cta."""
    if not primary_cta or not str(primary_cta).strip():
        raise AppError("Campaign must have a primary CTA before publishing the conversion page", status_code=400)
    cta_label = _extract_cta_from_structure(structure)
    if not cta_label or not str(cta_label).strip():
        raise AppError("Conversion page must contain a CTA section with a label", status_code=400)
    if str(cta_label).strip().lower() != str(primary_cta).strip().lower():
        raise AppError(
            f"Conversion page CTA must match campaign primary CTA. Page has '{cta_label}'; campaign has '{primary_cta}'.",
            status_code=400,
        )


def _extract_cta_from_structure(structure: dict | list | None) -> str | None:
    """Extract CTA label from React-driven structure (sections with type 'cta' or top-level cta)."""
    if structure is None:
        return None
    if isinstance(structure, dict):
        if structure.get("cta", {}).get("label"):
            return structure["cta"]["label"]
        sections = structure.get("sections")
        if isinstance(sections, list):
            for s in sections:
                if isinstance(s, dict) and (s.get("type") == "cta" or s.get("componentType") == "cta"):
                    return s.get("props", {}).get("label") or s.get("label")
        return None
    if isinstance(structure, list):
        for s in structure:
            if isinstance(s, dict) and (s.get("type") == "cta" or s.get("componentType") == "cta"):
                return s.get("props", {}).get("label") or s.get("label")
    return None


def validate_conversion_page_copy(structure: dict | list | None) -> None:
    """Run no-revenue-guarantees check on all copy in conversion page structure."""
    text = _flatten_structure_to_text(structure)
    validate_no_revenue_guarantees(text)


def _flatten_structure_to_text(structure: dict | list | None) -> str:
    """Recursively collect all string values from structure for governance check."""
    if structure is None:
        return ""
    if isinstance(structure, str):
        return structure
    if isinstance(structure, list):
        return " ".join(_flatten_structure_to_text(x) for x in structure)
    if isinstance(structure, dict):
        return " ".join(_flatten_structure_to_text(v) for v in structure.values())
    return ""


def check_proof_before_launch(pack_id: str, has_proof: bool, waiver_confirmed: bool) -> None:
    """Ensure proof exists or waiver confirmed before publish/export. Raise if not allowed."""
    if has_proof or waiver_confirmed:
        return
    raise AppError(
        "Proof required before launch: add at least one proof to the Proof Vault or confirm waiver.",
        status_code=400,
    )
