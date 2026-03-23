"""Google ID token verification helpers for GIS sign-in."""

from fastapi import status
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.core.errors import AppError, UnauthorizedError

GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleIdentity(BaseModel):
    sub: str
    email: EmailStr
    email_verified: bool


def verify_google_identity_token(token: str) -> GoogleIdentity:
    """Validate a Google ID token and return normalized identity claims."""
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise AppError(
            "Google authentication is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except Exception:
        raise AppError(
            "Google authentication dependency is not installed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_oauth_client_id,
        )
    except Exception:
        raise UnauthorizedError("Invalid or expired Google token")

    iss = claims.get("iss")
    if iss not in GOOGLE_ISSUERS:
        raise UnauthorizedError("Invalid Google token issuer")

    aud = claims.get("aud")
    if aud != settings.google_oauth_client_id:
        raise UnauthorizedError("Invalid Google token audience")

    sub = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip()
    email_verified = claims.get("email_verified") is True

    if not sub or not email:
        raise UnauthorizedError("Google token missing required claims")
    if not email_verified:
        raise UnauthorizedError("Google email is not verified")

    return GoogleIdentity(
        sub=sub,
        email=email,
        email_verified=True,
    )
