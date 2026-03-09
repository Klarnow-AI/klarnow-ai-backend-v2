"""Refresh-token session helpers."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.modules.packs.models import RefreshTokenSession

REFRESH_COOKIE_NAME = "klarnow_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_refresh_token_from_request(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE_NAME)


def set_refresh_token_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age_seconds = settings.refresh_token_expiry_days * 24 * 60 * 60
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_refresh_cookie_secure(settings),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age_seconds,
        expires=max_age_seconds,
    )


def clear_refresh_token_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=_refresh_cookie_secure(settings),
        samesite="lax",
    )


def create_refresh_token_session(db: Session, user_id: UUID) -> str:
    now = utc_now()
    raw_token = _generate_refresh_token()
    db.add(
        RefreshTokenSession(
            user_id=user_id,
            token_hash=_hash_refresh_token(raw_token),
            expires_at=_refresh_token_expiry(now),
            last_used_at=now,
        )
    )
    return raw_token


def rotate_refresh_token_session(db: Session, raw_token: str) -> tuple[RefreshTokenSession, str]:
    session = _get_refresh_token_session(db, raw_token)
    if not session:
        raise UnauthorizedError("Invalid or expired refresh token")

    now = utc_now()
    new_raw_token = _generate_refresh_token()
    session.token_hash = _hash_refresh_token(new_raw_token)
    session.expires_at = _refresh_token_expiry(now)
    session.last_used_at = now
    db.add(session)
    return session, new_raw_token


def revoke_refresh_token_session(db: Session, raw_token: str) -> None:
    token_hash = _hash_refresh_token(raw_token)
    (
        db.query(RefreshTokenSession)
        .filter(RefreshTokenSession.token_hash == token_hash)
        .delete(synchronize_session=False)
    )


def revoke_user_refresh_token_sessions(
    db: Session,
    user_id: UUID,
    *,
    exclude_raw_token: str | None = None,
) -> None:
    query = db.query(RefreshTokenSession).filter(RefreshTokenSession.user_id == user_id)
    if exclude_raw_token:
        query = query.filter(
            RefreshTokenSession.token_hash != _hash_refresh_token(exclude_raw_token)
        )
    query.delete(synchronize_session=False)


def _get_refresh_token_session(
    db: Session,
    raw_token: str,
) -> RefreshTokenSession | None:
    token_hash = _hash_refresh_token(raw_token)
    now = utc_now()
    session = (
        db.query(RefreshTokenSession)
        .filter(RefreshTokenSession.token_hash == token_hash)
        .first()
    )
    if not session:
        return None
    if session.expires_at <= now:
        return None
    return session


def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _refresh_token_expiry(now: datetime) -> datetime:
    settings = get_settings()
    return now + timedelta(days=settings.refresh_token_expiry_days)


def _refresh_cookie_secure(settings) -> bool:
    return settings.frontend_url.startswith("https://") or settings.app_env in {
        "production",
        "staging",
    }
