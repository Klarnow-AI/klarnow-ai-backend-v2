"""API Key management routes (Agency tier).

Provides endpoints for:
- GET    /api-keys          - List all API keys
- POST   /api-keys          - Create a new API key
- DELETE  /api-keys/{key_id} - Delete an API key
- POST   /api-keys/{key_id}/revoke - Revoke (deactivate) an API key
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.core.tier_gating import require_feature
from app.modules.api_keys.services import (
    generate_api_key,
    list_api_keys,
    revoke_api_key,
    delete_api_key,
)
from app.modules.packs.models import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    expires_at: datetime | None = None


class ApiKeyRead(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    usage_count: int
    last_used_at: str | None = None
    created_at: str
    expires_at: str | None = None


class ApiKeyCreatedRead(ApiKeyRead):
    """Returned only on creation. Includes the full raw key (shown once)."""
    raw_key: str


class ApiKeyListRead(BaseModel):
    keys: list[ApiKeyRead]
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ApiKeyListRead,
    dependencies=[Depends(require_feature("api_access"))],
)
def list_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the current user."""
    keys = list_api_keys(db, current_user.id)
    return ApiKeyListRead(
        keys=[
            ApiKeyRead(
                id=str(k.id),
                name=k.name,
                key_prefix=k.key_prefix,
                is_active=k.is_active,
                usage_count=k.usage_count,
                last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
                created_at=k.created_at.isoformat(),
                expires_at=k.expires_at.isoformat() if k.expires_at else None,
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.post(
    "",
    response_model=ApiKeyCreatedRead,
    status_code=201,
    dependencies=[Depends(require_feature("api_access"))],
)
def create_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new API key. The raw key is returned only in this response."""
    api_key, raw_key = generate_api_key(
        db,
        user_id=current_user.id,
        name=body.name,
        expires_at=body.expires_at,
    )
    return ApiKeyCreatedRead(
        id=str(api_key.id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        usage_count=api_key.usage_count,
        last_used_at=None,
        created_at=api_key.created_at.isoformat(),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        raw_key=raw_key,
    )


@router.post(
    "/{key_id}/revoke",
    response_model=dict,
    dependencies=[Depends(require_feature("api_access"))],
)
def revoke_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (deactivate) an API key."""
    success = revoke_api_key(db, current_user.id, key_id)
    if not success:
        raise NotFoundError("API key not found")
    return {"status": "revoked"}


@router.delete(
    "/{key_id}",
    response_model=dict,
    dependencies=[Depends(require_feature("api_access"))],
)
def remove_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete an API key."""
    success = delete_api_key(db, current_user.id, key_id)
    if not success:
        raise NotFoundError("API key not found")
    return {"status": "deleted"}
