"""Typed artifact schemas for the generation pipeline."""

from app.schemas.enums import (
    ApprovalDecision,
    ArtifactStatus,
    ArtifactType,
    ExportType,
    ProjectStatus,
    RunStatus,
    StageStatus,
    WebsiteType,
)
from app.schemas.normalized_input import NormalizedInput
from app.schemas.strategy import Strategy
from app.schemas.brand_identity import BrandIdentity
from app.schemas.website_blueprint import WebsiteBlueprint
from app.schemas.website_build import WebsiteBuild
from app.schemas.creative_campaign import CreativeCampaign
from app.schemas.qa_report import QAReport
from app.schemas.onboarding_form import OnboardingFormSubmission

ARTIFACT_SCHEMA_VERSION = 1

ARTIFACT_MODEL_BY_TYPE: dict[str, type] = {
    ArtifactType.NORMALIZED_INPUT: NormalizedInput,
    ArtifactType.STRATEGY: Strategy,
    ArtifactType.BRAND_IDENTITY: BrandIdentity,
    # ``WebsiteBlueprint`` is still imported because it lives inside
    # ``WebsiteBuild.blueprint`` — the builder owns planning internally, so
    # there's no standalone artifact type for it.
    ArtifactType.WEBSITE_BUILD: WebsiteBuild,
    ArtifactType.CREATIVE_CAMPAIGN: CreativeCampaign,
    ArtifactType.QA_REPORT: QAReport,
}


__all__ = [
    "ARTIFACT_MODEL_BY_TYPE",
    "ARTIFACT_SCHEMA_VERSION",
    "ApprovalDecision",
    "ArtifactStatus",
    "ArtifactType",
    "BrandIdentity",
    "CreativeCampaign",
    "ExportType",
    "NormalizedInput",
    "OnboardingFormSubmission",
    "ProjectStatus",
    "QAReport",
    "RunStatus",
    "StageStatus",
    "Strategy",
    "WebsiteBlueprint",
    "WebsiteBuild",
    "WebsiteType",
]
