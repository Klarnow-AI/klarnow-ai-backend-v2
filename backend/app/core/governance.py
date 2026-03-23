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
