"""API Key management service (Agency tier)."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.modules.api_keys.models import ApiKey

logger = get_logger("klarnow.api_keys")

# Prefix for all API keys to make them identifiable
KEY_PREFIX = "ka_"


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key(
    db: Session,
    user_id: UUID,
    name: str,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key and return (model, raw_key).

    The raw key is returned only once. After this, only the hash is stored.
    """
    raw_key = f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info("Created API key %s for user %s", api_key.id, user_id)
    return api_key, raw_key


def validate_api_key(db: Session, raw_key: str) -> ApiKey | None:
    """Validate a raw API key string and return the ApiKey record if valid.

    Also updates last_used_at and usage_count.
    """
    key_hash = _hash_key(raw_key)
    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True,  # noqa: E712
    ).first()

    if not api_key:
        return None

    # Check expiry
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None

    # Update usage stats
    api_key.last_used_at = datetime.now(timezone.utc)
    api_key.usage_count = (api_key.usage_count or 0) + 1
    db.commit()

    return api_key


def list_api_keys(db: Session, user_id: UUID) -> list[ApiKey]:
    """List all API keys for a user (active and inactive)."""
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )


def revoke_api_key(db: Session, user_id: UUID, key_id: UUID) -> bool:
    """Revoke (deactivate) an API key. Returns True if found and revoked."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == user_id,
    ).first()
    if not api_key:
        return False

    api_key.is_active = False
    db.commit()
    logger.info("Revoked API key %s for user %s", key_id, user_id)
    return True


def delete_api_key(db: Session, user_id: UUID, key_id: UUID) -> bool:
    """Permanently delete an API key. Returns True if found and deleted."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == user_id,
    ).first()
    if not api_key:
        return False

    db.delete(api_key)
    db.commit()
    logger.info("Deleted API key %s for user %s", key_id, user_id)
    return True
