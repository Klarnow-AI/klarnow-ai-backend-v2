"""Helpers for targeted onboarding stage repairs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.packs.onboarding.constants import (
    PUBLIC_STAGE_BRAND_IDENTITY,
    PUBLIC_STAGE_BRAND_OS,
    PUBLIC_STAGE_POSTER_FLYERS,
    PUBLIC_STAGE_WEBSITE,
    STAGE_BRAND_IDENTITY,
    STAGE_BRAND_OS,
    STAGE_LOGO,
    STAGE_NORMALIZE_INPUT,
    STAGE_POSTER_FLYERS,
    STAGE_QA_REVIEW,
    STAGE_STARTER_BRAND,
    STAGE_VIDEO_BRIEFS,
    STAGE_VIDEO_RENDER,
    STAGE_WEBSITE,
)

REPAIRABLE_STAGE_ALIASES: dict[str, str] = {
    STAGE_NORMALIZE_INPUT: STAGE_NORMALIZE_INPUT,
    PUBLIC_STAGE_BRAND_OS: PUBLIC_STAGE_BRAND_OS,
    STAGE_BRAND_OS: PUBLIC_STAGE_BRAND_OS,
    PUBLIC_STAGE_BRAND_IDENTITY: PUBLIC_STAGE_BRAND_IDENTITY,
    STAGE_BRAND_IDENTITY: PUBLIC_STAGE_BRAND_IDENTITY,
    STAGE_STARTER_BRAND: PUBLIC_STAGE_BRAND_IDENTITY,
    STAGE_LOGO: PUBLIC_STAGE_BRAND_IDENTITY,
    PUBLIC_STAGE_WEBSITE: PUBLIC_STAGE_WEBSITE,
    STAGE_WEBSITE: PUBLIC_STAGE_WEBSITE,
    PUBLIC_STAGE_POSTER_FLYERS: PUBLIC_STAGE_POSTER_FLYERS,
    STAGE_POSTER_FLYERS: PUBLIC_STAGE_POSTER_FLYERS,
    STAGE_VIDEO_BRIEFS: STAGE_VIDEO_BRIEFS,
    STAGE_VIDEO_RENDER: STAGE_VIDEO_RENDER,
    STAGE_QA_REVIEW: STAGE_QA_REVIEW,
}

REPAIRABLE_PUBLIC_STAGES: tuple[str, ...] = (
    STAGE_NORMALIZE_INPUT,
    PUBLIC_STAGE_BRAND_OS,
    PUBLIC_STAGE_BRAND_IDENTITY,
    PUBLIC_STAGE_WEBSITE,
    PUBLIC_STAGE_POSTER_FLYERS,
    STAGE_VIDEO_BRIEFS,
    STAGE_VIDEO_RENDER,
    STAGE_QA_REVIEW,
)

_STAGE_SEQUENCE_BY_PUBLIC_STAGE: dict[str, tuple[str, ...]] = {
    STAGE_NORMALIZE_INPUT: (
        STAGE_NORMALIZE_INPUT,
        STAGE_BRAND_OS,
        STAGE_BRAND_IDENTITY,
        STAGE_WEBSITE,
        STAGE_POSTER_FLYERS,
        STAGE_VIDEO_BRIEFS,
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    PUBLIC_STAGE_BRAND_OS: (
        STAGE_BRAND_OS,
        STAGE_BRAND_IDENTITY,
        STAGE_WEBSITE,
        STAGE_POSTER_FLYERS,
        STAGE_VIDEO_BRIEFS,
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    PUBLIC_STAGE_BRAND_IDENTITY: (
        STAGE_BRAND_IDENTITY,
        STAGE_WEBSITE,
        STAGE_POSTER_FLYERS,
        STAGE_VIDEO_BRIEFS,
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    PUBLIC_STAGE_WEBSITE: (
        STAGE_WEBSITE,
        STAGE_POSTER_FLYERS,
        STAGE_VIDEO_BRIEFS,
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    PUBLIC_STAGE_POSTER_FLYERS: (
        STAGE_POSTER_FLYERS,
        STAGE_VIDEO_BRIEFS,
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    STAGE_VIDEO_BRIEFS: (
        STAGE_VIDEO_BRIEFS,
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    STAGE_VIDEO_RENDER: (
        STAGE_VIDEO_RENDER,
        STAGE_QA_REVIEW,
    ),
    STAGE_QA_REVIEW: (STAGE_QA_REVIEW,),
}

_PRIMARY_STAGES_BY_PUBLIC_STAGE: dict[str, tuple[str, ...]] = {
    STAGE_NORMALIZE_INPUT: (STAGE_NORMALIZE_INPUT,),
    PUBLIC_STAGE_BRAND_OS: (STAGE_BRAND_OS,),
    PUBLIC_STAGE_BRAND_IDENTITY: (STAGE_BRAND_IDENTITY,),
    PUBLIC_STAGE_WEBSITE: (STAGE_WEBSITE,),
    PUBLIC_STAGE_POSTER_FLYERS: (STAGE_POSTER_FLYERS,),
    STAGE_VIDEO_BRIEFS: (STAGE_VIDEO_BRIEFS,),
    STAGE_VIDEO_RENDER: (STAGE_VIDEO_RENDER,),
    STAGE_QA_REVIEW: (STAGE_QA_REVIEW,),
}


@dataclass(frozen=True)
class OnboardingRepairPlan:
    requested_stage: str
    selected_stages: tuple[str, ...]


@dataclass(frozen=True)
class QARepairRecommendation:
    stage_name: str | None
    reason: str | None
    auto_repairable: bool


def normalize_repair_stage(stage_name: str) -> str:
    normalized = REPAIRABLE_STAGE_ALIASES.get(str(stage_name or "").strip())
    if not normalized:
        allowed = ", ".join(REPAIRABLE_PUBLIC_STAGES)
        raise ValueError(f"Unsupported onboarding stage '{stage_name}'. Allowed values: {allowed}.")
    return normalized


def build_repair_plan(stage_name: str, *, include_downstream: bool = True) -> OnboardingRepairPlan:
    requested_stage = normalize_repair_stage(stage_name)
    if include_downstream:
        selected_stages = _STAGE_SEQUENCE_BY_PUBLIC_STAGE[requested_stage]
    else:
        primary_stages = list(_PRIMARY_STAGES_BY_PUBLIC_STAGE[requested_stage])
        if requested_stage != STAGE_QA_REVIEW and STAGE_QA_REVIEW not in primary_stages:
            primary_stages.append(STAGE_QA_REVIEW)
        selected_stages = tuple(primary_stages)
    return OnboardingRepairPlan(
        requested_stage=requested_stage,
        selected_stages=selected_stages,
    )


def _report_strings(report: Any, field_name: str) -> list[str]:
    raw = getattr(report, field_name, None)
    if isinstance(raw, list):
        return [str(item or "").strip() for item in raw if str(item or "").strip()]
    return []


def _contains_any(checks: list[str], *needles: str) -> bool:
    lowered_checks = [check.lower() for check in checks]
    for needle in needles:
        query = str(needle or "").strip().lower()
        if query and any(query in check for check in lowered_checks):
            return True
    return False


def recommend_repair_from_qa(report: Any) -> QARepairRecommendation:
    existing_stage = str(getattr(report, "recommended_repair_stage", "") or "").strip()
    if existing_stage:
        return QARepairRecommendation(
            stage_name=existing_stage,
            reason=str(getattr(report, "recommended_repair_reason", "") or "").strip() or None,
            auto_repairable=bool(getattr(report, "auto_repairable", False)),
        )

    failed_checks = _report_strings(report, "failed_checks")
    warning_checks = _report_strings(report, "warning_checks")
    prioritized_checks = failed_checks or warning_checks

    if _contains_any(prioritized_checks, "normalized business profile is missing", "normalized profile still has missing fields"):
        return QARepairRecommendation(
            stage_name=STAGE_NORMALIZE_INPUT,
            reason="Refresh the normalized business profile before downstream stages.",
            auto_repairable=_contains_any(failed_checks, "normalized business profile is missing"),
        )
    if _contains_any(prioritized_checks, "brand os is missing", "tone cues differ between normalized input and brand os"):
        return QARepairRecommendation(
            stage_name=PUBLIC_STAGE_BRAND_OS,
            reason="Refresh Brand OS so strategy and downstream assets share the same source of truth.",
            auto_repairable=_contains_any(failed_checks, "brand os is missing"),
        )
    if _contains_any(prioritized_checks, "brand identity artifact is missing", "visual identity signals are thin or missing"):
        return QARepairRecommendation(
            stage_name=PUBLIC_STAGE_BRAND_IDENTITY,
            reason="Refresh the brand identity layer to restore palette, logo, and voice rules.",
            auto_repairable=_contains_any(failed_checks, "brand identity artifact is missing"),
        )
    if _contains_any(prioritized_checks, "website blueprint artifact is missing", "website output is missing or still on the placeholder app"):
        return QARepairRecommendation(
            stage_name=PUBLIC_STAGE_WEBSITE,
            reason="Regenerate the website blueprint and builder output.",
            auto_repairable=_contains_any(failed_checks, "website output is missing or still on the placeholder app"),
        )
    if _contains_any(prioritized_checks, "creative brief artifact is missing", "starter poster pack is incomplete"):
        return QARepairRecommendation(
            stage_name=PUBLIC_STAGE_POSTER_FLYERS,
            reason="Rebuild the creative brief and starter poster set.",
            auto_repairable=_contains_any(failed_checks, "starter poster pack is incomplete"),
        )
    if _contains_any(prioritized_checks, "video brief artifact is missing"):
        return QARepairRecommendation(
            stage_name=STAGE_VIDEO_BRIEFS,
            reason="Rebuild the video briefs before rendering videos.",
            auto_repairable=_contains_any(failed_checks, "video brief artifact is missing"),
        )
    if _contains_any(prioritized_checks, "video render artifact is missing", "starter video output is incomplete"):
        return QARepairRecommendation(
            stage_name=STAGE_VIDEO_RENDER,
            reason="Rerun video rendering from the latest brief bundle.",
            auto_repairable=_contains_any(failed_checks, "starter video output is incomplete"),
        )
    return QARepairRecommendation(stage_name=None, reason=None, auto_repairable=False)


def build_repair_plan_from_qa(
    report: Any,
    *,
    include_downstream: bool = True,
) -> OnboardingRepairPlan:
    recommendation = recommend_repair_from_qa(report)
    if not recommendation.stage_name:
        raise ValueError("The latest QA report does not contain a repairable stage recommendation.")
    return build_repair_plan(recommendation.stage_name, include_downstream=include_downstream)
