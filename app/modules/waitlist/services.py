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
    first_name: str | None,
    role: str | None,
    goal: str | None,
    source: str | None,
) -> WaitlistSignup:
    changed = False
    if first_name and signup.first_name != first_name:
        signup.first_name = first_name
        changed = True
    if role and signup.role != role:
        signup.role = role
        changed = True
    if goal and signup.goal != goal:
        signup.goal = goal
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
    first_name: str | None = None,
    role: str | None = None,
    goal: str | None = None,
    source: str | None = None,
) -> WaitlistSubscribeResult:
    normalized_email = _normalize_email(email)
    cleaned_first_name = _clean_optional_text(first_name)
    cleaned_role = _clean_optional_text(role)
    cleaned_goal = _clean_optional_text(goal)
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
            first_name=cleaned_first_name,
            role=cleaned_role,
            goal=cleaned_goal,
            source=cleaned_source,
        )
        return WaitlistSubscribeResult(signup=signup, already_subscribed=True)

    signup = WaitlistSignup(
        email=normalized_email,
        first_name=cleaned_first_name,
        role=cleaned_role,
        goal=cleaned_goal,
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
            first_name=cleaned_first_name,
            role=cleaned_role,
            goal=cleaned_goal,
            source=cleaned_source,
        )
        return WaitlistSubscribeResult(signup=signup, already_subscribed=True)

    db.refresh(signup)
    return WaitlistSubscribeResult(signup=signup, already_subscribed=False)
