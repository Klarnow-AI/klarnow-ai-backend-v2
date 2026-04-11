"""Tier gating utilities.

Provides decorators and helpers to enforce feature access
based on the user's subscription tier.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.modules.billing.constants import TIERS, VALID_TIERS
from app.modules.packs.models import User


def _billing_enforced() -> bool:
    """Return False when BILLING_ENFORCEMENT_ENABLED=false (dev bypass)."""
    from app.core.config import get_settings
    return get_settings().billing_enforcement_enabled


def get_user_tier(user: User) -> str:
    """Get the effective tier for a user."""
    tier = getattr(user, "tier", "free") or "free"
    return tier if tier in VALID_TIERS else "free"


def check_feature(user: User, feature: str) -> bool:
    """Check if a user's tier grants access to a specific feature.

    Args:
        user: The authenticated user
        feature: A key from TierDefinition.limits (e.g. 'website_export', 'api_access')

    Returns:
        True if the feature is enabled for the user's tier
    """
    if not _billing_enforced():
        return True

    tier = get_user_tier(user)
    tier_def = TIERS.get(tier, TIERS["free"])
    value = tier_def.limits.get(feature)

    if value is None:
        # None means unlimited (e.g. max_projects for Agency)
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    return bool(value)


def require_feature(feature: str, message: str | None = None) -> Callable:
    """FastAPI dependency that raises 403 if the user's tier lacks a feature.

    Usage:
        @router.get("/something")
        def my_endpoint(
            current_user: User = Depends(get_current_user),
            _gate: None = Depends(require_feature("svg_export")),
        ):
            ...
    """
    from app.core.auth.deps import get_current_user

    def dependency(current_user: User = Depends(get_current_user)) -> None:
        if not _billing_enforced():
            return
        if not check_feature(current_user, feature):
            tier = get_user_tier(current_user)
            detail = message or f"Your current plan ({tier}) does not include this feature. Please upgrade."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
    return dependency


def require_tier(minimum_tier: str, message: str | None = None) -> Callable:
    """FastAPI dependency that requires at least a specific tier.

    Tier hierarchy: free < starter < pro < agency

    Usage:
        @router.get("/pro-feature")
        def my_endpoint(
            current_user: User = Depends(get_current_user),
            _gate: None = Depends(require_tier("pro")),
        ):
            ...
    """
    tier_rank = {"free": 0, "starter": 1, "pro": 2, "agency": 3}

    from app.core.auth.deps import get_current_user

    def dependency(current_user: User = Depends(get_current_user)) -> None:
        if not _billing_enforced():
            return
        user_tier = get_user_tier(current_user)
        user_rank = tier_rank.get(user_tier, 0)
        required_rank = tier_rank.get(minimum_tier, 0)

        if user_rank < required_rank:
            detail = message or f"This feature requires the {minimum_tier.title()} plan or higher. You are on {user_tier.title()}."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
    return dependency


def get_project_limit(user: User) -> int | None:
    """Get the max number of projects allowed for a user's tier.

    Returns None for unlimited.
    """
    if not _billing_enforced():
        return None  # unlimited in dev mode
    tier = get_user_tier(user)
    tier_def = TIERS.get(tier, TIERS["free"])
    return tier_def.limits.get("max_projects")
