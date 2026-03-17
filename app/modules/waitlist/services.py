"""Waitlist services."""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.waitlist.models import WaitlistSignup


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(frozen=True)
class WaitlistSubscribeResult:
    signup: WaitlistSignup
    already_subscribed: bool


def _merge_signup_details(
    db: Session,
    signup: WaitlistSignup,
    *,
    name: str | None,
    source: str | None,
) -> WaitlistSignup:
    changed = False
    if name and signup.name != name:
        signup.name = name
        changed = True
    if source and signup.source != source:
        signup.source = source
        changed = True
    if changed:
        db.commit()
        db.refresh(signup)
    return signup


@log_service_action()
def subscribe(
    db: Session,
    *,
    email: str,
    name: str | None = None,
    source: str | None = None,
) -> WaitlistSubscribeResult:
    normalized_email = _normalize_email(email)
    cleaned_name = _clean_optional_text(name)
    cleaned_source = _clean_optional_text(source)

    existing = (
        db.query(WaitlistSignup)
        .filter(WaitlistSignup.email == normalized_email)
        .first()
    )
    if existing:
        signup = _merge_signup_details(
            db,
            existing,
            name=cleaned_name,
            source=cleaned_source,
        )
        return WaitlistSubscribeResult(signup=signup, already_subscribed=True)

    signup = WaitlistSignup(
        email=normalized_email,
        name=cleaned_name,
        source=cleaned_source,
    )
    db.add(signup)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(WaitlistSignup)
            .filter(WaitlistSignup.email == normalized_email)
            .first()
        )
        if existing is None:
            raise
        signup = _merge_signup_details(
            db,
            existing,
            name=cleaned_name,
            source=cleaned_source,
        )
        return WaitlistSubscribeResult(signup=signup, already_subscribed=True)

    db.refresh(signup)
    return WaitlistSubscribeResult(signup=signup, already_subscribed=False)
