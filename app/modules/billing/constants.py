"""Billing tier definitions and Stripe price mapping."""
from __future__ import annotations

from dataclasses import dataclass

VALID_TIERS = ("free", "starter", "pro", "agency")

# These Stripe Price IDs should be set in environment/config.
TIER_PRICE_MAP: dict[str, str | None] = {
    "free": None,
    "starter": "price_starter_monthly",
    "pro": "price_pro_monthly",
    "agency": "price_agency_monthly",
}


@dataclass(frozen=True)
class TierDefinition:
    key: str
    name: str
    price_gbp: int
    description: str
    features: tuple[str, ...]
    limits: dict[str, int | bool | None]


TIERS: dict[str, TierDefinition] = {
    "free": TierDefinition(
        key="free",
        name="Free",
        price_gbp=0,
        description="Try the platform with limited outputs",
        features=(
            "1 project",
            "Strategy + identity generation",
            "Basic website generation",
            "Campaign copy only",
        ),
        limits={
            "max_projects": 1,
            "full_asset_downloads": False,
            "website_export": False,
            "api_access": False,
            "white_label": False,
        },
    ),
    "starter": TierDefinition(
        key="starter",
        name="Starter",
        price_gbp=49,
        description="Everything you need to launch a brand",
        features=(
            "3 projects",
            "Full pipeline generation",
            "Website code bundle export",
            "Campaign asset specs",
            "Brand package export",
            "QA review",
        ),
        limits={
            "max_projects": 3,
            "full_asset_downloads": True,
            "website_export": True,
            "api_access": False,
            "white_label": False,
        },
    ),
    "pro": TierDefinition(
        key="pro",
        name="Pro",
        price_gbp=129,
        description="Professional brand builder with full creative suite",
        features=(
            "10 projects",
            "Everything in Starter",
            "Priority generation queue",
            "Version history and comparison",
            "Advanced design system tokens",
        ),
        limits={
            "max_projects": 10,
            "full_asset_downloads": True,
            "website_export": True,
            "api_access": False,
            "white_label": False,
        },
    ),
    "agency": TierDefinition(
        key="agency",
        name="Agency",
        price_gbp=299,
        description="Scale brand creation for your clients",
        features=(
            "Unlimited projects",
            "Everything in Pro",
            "API access",
            "White-label exports",
            "Bulk generation",
            "Priority support",
        ),
        limits={
            "max_projects": None,  # Unlimited
            "full_asset_downloads": True,
            "website_export": True,
            "api_access": True,
            "white_label": True,
        },
    ),
}
