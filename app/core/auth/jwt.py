from datetime import datetime, timezone, timedelta
from uuid import UUID

import jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


class TokenPayload(BaseModel):
    sub: str  # user id
    exp: datetime
    type: str = "access"


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expiry_time)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm="HS256",
    )


def verify_token(token: str) -> TokenPayload:
    settings = get_settings()
    if not settings.secret_key:
        raise UnauthorizedError("Auth not configured")
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token")
