from datetime import datetime, timezone, timedelta
from uuid import UUID

import jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

_JWT_CACHE_PREFIX = "jwt:payload:"


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


def _cache_key(token: str) -> str:
    # Use last 16 chars as a cheap discriminator; full token is the cache value key
    return f"{_JWT_CACHE_PREFIX}{token[-16:]}"


def verify_token(token: str) -> TokenPayload:
    settings = get_settings()
    if not settings.secret_key:
        raise UnauthorizedError("Auth not configured")

    # --- Redis cache lookup ---
    redis = None
    try:
        import redis as redis_lib
        url = settings.redis_url
        if url:
            redis = redis_lib.Redis.from_url(url)
            cached = redis.hgetall(_cache_key(token))
            if cached and cached.get("token") == token:
                return TokenPayload(
                    sub=cached["sub"],
                    exp=datetime.fromtimestamp(float(cached["exp"]), tz=timezone.utc),
                )
    except Exception:
        redis = None  # cache unavailable — fall through to full decode

    # --- Full decode ---
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        token_payload = TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token")

    # --- Populate cache with TTL = remaining token lifetime ---
    if redis is not None:
        try:
            now = datetime.now(timezone.utc)
            ttl = int((token_payload.exp - now).total_seconds())
            if ttl > 0:
                key = _cache_key(token)
                redis.hset(key, mapping={
                    "token": token,
                    "sub": token_payload.sub,
                    "exp": str(payload["exp"]),
                })
                redis.expire(key, ttl)
        except Exception:
            pass  # cache write failure is non-fatal

    return token_payload
