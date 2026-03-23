"""Proof fallback: generate process, policy, or founder proof when none exist."""

from app.modules.packs.models import Pack


def generate_process_proof(pack: Pack) -> str:
    """Generate process proof (e.g. step-by-step or methodology)."""
    offer = (pack.offer_one_liner or "your service").strip()
    return f"Our proven process: We take a structured approach to deliver {offer}. Clear steps, no surprises."


def generate_policy_proof(pack: Pack) -> str:
    """Generate policy proof (e.g. guarantee or commitment)."""
    return "We stand behind our work. If you're not satisfied with the outcome, we'll work with you until it's right."


def generate_founder_proof(pack: Pack) -> str:
    """Generate founder proof (e.g. experience or credibility)."""
    brand = (pack.brand_name or "We").strip()
    return f"{brand} is built on real experience and a focus on results. We've helped businesses like yours get to the next level."


def generate_one_proof(pack: Pack, proof_type: str = "process") -> str:
    """Generate one proof by type: process, policy, or founder."""
    if proof_type == "policy":
        return generate_policy_proof(pack)
    if proof_type == "founder":
        return generate_founder_proof(pack)
    return generate_process_proof(pack)
