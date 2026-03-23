"""Shared slowapi limiter instance."""

from slowapi import Limiter
from slowapi.util import get_remote_address


def _make_limiter() -> Limiter:
    from app.core.config import get_settings

    redis_url = get_settings().redis_url
    return Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url or "memory://",
    )


limiter = _make_limiter()
