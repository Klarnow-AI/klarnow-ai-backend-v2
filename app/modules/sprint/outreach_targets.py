"""Outreach targets by business type."""

from typing import TypedDict


class OutreachTargets(TypedDict):
    """Outreach targets for a business type."""
    dms: int | None
    dms_or_calls: int | None
    comments: int | None
    broadcasts: int | None
    followups: int
    voice_notes: int | None
    referral_asks: int | None


OUTREACH_TARGETS: dict[str, OutreachTargets] = {
    "product": {
        "dms": 20,
        "dms_or_calls": None,
        "comments": 10,
        "broadcasts": 1,
        "followups": 10,
        "voice_notes": None,
        "referral_asks": None,
    },
    "service": {
        "dms": None,
        "dms_or_calls": 15,  # either DMs or calls
        "comments": 10,
        "broadcasts": None,
        "followups": 5,
        "voice_notes": None,
        "referral_asks": 3,
    },
    "coach": {
        "dms": 10,
        "dms_or_calls": None,
        "comments": 10,
        "broadcasts": None,
        "followups": 5,
        "voice_notes": 5,
        "referral_asks": None,
    },
}


def get_daily_outreach_target(business_type: str) -> int:
    """
    MVP: return single counter target (primary outreach activities).
    
    IMPORTANT: These targets are per SPRINT DAY completion, not per calendar day.
    To complete Sprint Day 4, user must log 15 outreach activities FOR Day 4.
    Users can complete multiple sprint days in one calendar session.
    """
    targets = OUTREACH_TARGETS.get(business_type, OUTREACH_TARGETS["product"])
    # For MVP, we track one counter only - use the DMs/calls count
    return targets.get("dms") or targets.get("dms_or_calls") or 10


def get_daily_followup_target(business_type: str) -> int:
    """Get follow-up target per sprint day."""
    targets = OUTREACH_TARGETS.get(business_type, OUTREACH_TARGETS["product"])
    return targets["followups"]
