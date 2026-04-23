"""Enumerations for the project/artifact domain."""

from enum import StrEnum


class ArtifactType(StrEnum):
    NORMALIZED_INPUT = "normalized_input"
    STRATEGY = "strategy"
    # Merged visual stage — replaces the old split between textual ``IDENTITY``
    # (archetype, taglines, voice) and token-based ``DESIGN_SYSTEM`` (colors,
    # typography). Voice / taglines now live on :class:`Strategy` because
    # they're text that *feeds* downstream generation, not a visual deliverable.
    BRAND_IDENTITY = "brand_identity"
    # No standalone WEBSITE_BLUEPRINT artifact anymore — the builder owns
    # planning internally and emits the plan embedded in ``WEBSITE_BUILD``.
    WEBSITE_BUILD = "website_build"
    CREATIVE_CAMPAIGN = "creative_campaign"
    QA_REPORT = "qa_report"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    ONBOARDING = "onboarding"
    GENERATING = "generating"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class WebsiteType(StrEnum):
    LANDING_PAGE = "landing_page"
    BROCHURE_STATIC = "brochure_static"
    SERVICE_LEAD_GEN = "service_lead_gen"
    # Phase 2
    BOOKING_SITE = "booking_site"
    ECOMMERCE = "ecommerce"


class ExportType(StrEnum):
    BRAND_PACKAGE = "brand_package"
    WEBSITE_BUNDLE = "website_bundle"
    ASSET_PACKAGE = "asset_package"
    FULL_PROJECT = "full_project"
