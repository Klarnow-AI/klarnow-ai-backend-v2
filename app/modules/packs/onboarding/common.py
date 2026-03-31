"""Common onboarding job helpers and lightweight value utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.packs.models import utc_now


def _text_or_none(value: Any, *, limit: int | None = None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if limit is not None:
        return text[:limit]
    return text


def _summary_text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (list, tuple, set)):
        parts = [_summary_text_or_none(item) for item in value]
        cleaned_parts = [part for part in parts if part]
        if not cleaned_parts:
            return None
        return ", ".join(cleaned_parts)
    text = str(value).strip()
    return text or None


@dataclass(slots=True)
class OnboardingRunResult:
    retry: bool
    attempt: int
    clear_dispatch: bool


class OnboardingPauseRequested(RuntimeError):
    """Raised when a user requests onboarding generation to pause safely."""


def _iso_now() -> str:
    return utc_now().isoformat()

