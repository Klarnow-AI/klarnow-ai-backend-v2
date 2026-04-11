"""API key authentication middleware for external access.

Allows Agency-tier users to authenticate via X-API-Key header
instead of the standard JWT Bearer token.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.core.logging import get_logger
from app.core.tier_gating import check_feature
from app.modules.api_keys.services import validate_api_key

logger = get_logger("klarnow.auth.api_key")


def get_api_key_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """Extract and validate an API key from X-API-Key header.

    Returns the user associated with the key, or raises 401/403.

    Usage as an alternative auth dependency:
        @router.get("/external/data")
        def external_endpoint(
            current_user = Depends(get_api_key_user),
        ):
            ...
    """
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    api_key = validate_api_key(db, api_key_header)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    user = api_key.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key user not found",
        )

    # Verify the user still has API access (tier might have been downgraded)
    if not check_feature(user, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your current plan does not include API access. Please upgrade to Agency.",
        )

    return user


def get_current_user_or_api_key(
    request: Request,
    db: Session = Depends(get_db),
):
    """Hybrid auth dependency: accepts either Bearer JWT or X-API-Key.

    Checks X-API-Key first, falls back to standard JWT auth.
    Useful for endpoints that need to work for both dashboard users
    and external API consumers.
    """
    api_key_header = request.headers.get("X-API-Key")

    if api_key_header:
        return get_api_key_user(request, db)

    # Fall back to standard JWT auth
    from app.core.auth.deps import get_current_user_id

    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    bearer = HTTPBearer(auto_error=False)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Provide either X-API-Key or Bearer token.",
        )

    from app.core.auth.jwt import verify_token
    from app.core.auth.deps import LazyCurrentUser
    from uuid import UUID

    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)
    uid = UUID(payload.sub)
    return LazyCurrentUser(uid, db)
