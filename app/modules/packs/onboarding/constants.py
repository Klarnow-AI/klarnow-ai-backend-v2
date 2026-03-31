"""Onboarding job constants and generated-content patterns."""

from __future__ import annotations

import re

from app.core.logging import get_logger

ONBOARDING_JOB_KEY = "_onboarding_job"
ONBOARDING_JOB_MAX_ATTEMPTS = 3
ONBOARDING_JOB_EVENTS_MAX = 100
ACTIVE_ONBOARDING_JOB_STATUSES = {"queued", "running"}
NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY = "_normalize_input_fingerprint"
STARTER_BRAND_INPUT_FINGERPRINT_KEY = "_starter_brand_input_fingerprint"
BRAND_IDENTITY_INPUT_FINGERPRINT_KEY = "_brand_identity_input_fingerprint"
BRAND_OS_INPUT_FINGERPRINT_KEY = "_onboarding_brand_os_input_fingerprint"
LOGO_INPUT_FINGERPRINT_KEY = "_final_logo_input_fingerprint"
WEBSITE_INPUT_FINGERPRINT_KEY = "_website_input_fingerprint"
POSTER_FLYERS_INPUT_FINGERPRINT_KEY = "_poster_flyers_input_fingerprint"
VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY = "_video_briefs_input_fingerprint"
VIDEO_RENDER_INPUT_FINGERPRINT_KEY = "_video_render_input_fingerprint"
QA_REVIEW_INPUT_FINGERPRINT_KEY = "_qa_review_input_fingerprint"

STAGE_NORMALIZE_INPUT = "normalize_input"
STAGE_STARTER_BRAND = "starter_brand"
STAGE_BRAND_IDENTITY = "brand_identity"
STAGE_BRAND_OS = "brand_os"
STAGE_LOGO = "logo"
STAGE_WEBSITE = "website"
STAGE_POSTER_FLYERS = "poster_flyers"
STAGE_VIDEO_BRIEFS = "video_briefs"
STAGE_VIDEO_RENDER = "video_render"
STAGE_QA_REVIEW = "qa_review"
ONBOARDING_JOB_STAGES = (
    STAGE_NORMALIZE_INPUT,
    STAGE_BRAND_OS,
    STAGE_BRAND_IDENTITY,
    STAGE_WEBSITE,
    STAGE_POSTER_FLYERS,
    STAGE_VIDEO_BRIEFS,
    STAGE_VIDEO_RENDER,
    STAGE_QA_REVIEW,
)

PUBLIC_STAGE_BRAND_OS = "brand_os"
PUBLIC_STAGE_BRAND_IDENTITY = "brand_identity"
PUBLIC_STAGE_WEBSITE = "website"
PUBLIC_STAGE_POSTER_FLYERS = "poster_flyers"
PUBLIC_STAGE_VIDEOS = "videos"
PUBLIC_ONBOARDING_STAGE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (PUBLIC_STAGE_BRAND_OS, (STAGE_BRAND_OS,)),
    (PUBLIC_STAGE_BRAND_IDENTITY, (STAGE_BRAND_IDENTITY,)),
    (PUBLIC_STAGE_WEBSITE, (STAGE_WEBSITE,)),
    (PUBLIC_STAGE_POSTER_FLYERS, (STAGE_POSTER_FLYERS,)),
    (PUBLIC_STAGE_VIDEOS, (STAGE_VIDEO_BRIEFS, STAGE_VIDEO_RENDER)),
)
PUBLIC_STAGE_ALIASES = {
    STAGE_NORMALIZE_INPUT: PUBLIC_STAGE_BRAND_OS,
    STAGE_BRAND_IDENTITY: PUBLIC_STAGE_BRAND_IDENTITY,
    STAGE_STARTER_BRAND: PUBLIC_STAGE_BRAND_IDENTITY,
    STAGE_BRAND_OS: PUBLIC_STAGE_BRAND_OS,
    STAGE_LOGO: PUBLIC_STAGE_BRAND_IDENTITY,
    STAGE_WEBSITE: PUBLIC_STAGE_WEBSITE,
    STAGE_POSTER_FLYERS: PUBLIC_STAGE_POSTER_FLYERS,
    STAGE_VIDEO_BRIEFS: PUBLIC_STAGE_VIDEOS,
    STAGE_VIDEO_RENDER: PUBLIC_STAGE_VIDEOS,
    STAGE_QA_REVIEW: PUBLIC_STAGE_VIDEOS,
}

logger = get_logger("klarnow.onboarding")

_IGNORED_ONBOARDING_INPUT_KEYS = {
    ONBOARDING_JOB_KEY,
    NORMALIZE_INPUT_INPUT_FINGERPRINT_KEY,
    STARTER_BRAND_INPUT_FINGERPRINT_KEY,
    BRAND_IDENTITY_INPUT_FINGERPRINT_KEY,
    BRAND_OS_INPUT_FINGERPRINT_KEY,
    LOGO_INPUT_FINGERPRINT_KEY,
    WEBSITE_INPUT_FINGERPRINT_KEY,
    POSTER_FLYERS_INPUT_FINGERPRINT_KEY,
    VIDEO_BRIEFS_INPUT_FINGERPRINT_KEY,
    VIDEO_RENDER_INPUT_FINGERPRINT_KEY,
    QA_REVIEW_INPUT_FINGERPRINT_KEY,
    "_onboarding_artifacts",
    "generated_logo_url",
    "transparent_logo_url",
    "wordmark_svg_or_url",
    "palette",
    "starter_brand_job_id",
    "starter_brand_completed_at",
    "suggested_logos",
    "onboarding_brand_os_id",
    "onboarding_brand_os_job_id",
    "onboarding_brand_os_completed_at",
    "final_logo_job_id",
    "final_logo_completed_at",
    "onboarding_website_project_id",
    "onboarding_website_generated_at",
    "onboarding_poster_flyers_generated_at",
    "onboarding_videos_generated_at",
}

_DEFAULT_BUILDER_APP = """export default function App() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <h1 className="text-3xl font-[600] text-gray-800">
        Describe your website to get started
      </h1>
    </div>
  );
}
"""
_DEFAULT_BUILDER_APP_MARKER = "Describe your website to get started"
_AUTO_WEBSITE_PROMPT = (
    "Build the first launch-ready website for this brand now. "
    "Skip questions and return a complete /App.tsx with a strong hero, offer, proof, "
    "process, FAQ, and a lead capture section."
)
_AUTO_POSTER_PROMPT = """Create the next starter poster concept for my brand.
Hard rules:
- Use the existing pack and brand context as the source of truth.
- Return only the files required by the system instructions for this concept.
- Generate all required sizes for the concept in one pass.
- Each file must be self-contained TSX with inline styles only."""
_AUTO_POSTER_QUEUE_CONFIG: tuple[tuple[str, str, str], ...] = (
    ("v1", "Concept 1", "Objection buster"),
    ("v2", "Concept 2", "Offer spotlight"),
    ("v3", "Concept 3", "Proof-led poster"),
    ("v4", "Concept 4", "Hero headline"),
)
_AUTO_POSTER_SIZE_IDS = ("4x5", "9x16", "16x9", "1x1")
_AUTO_VIDEO_COUNT = 4
_FILE_TAG_RE = re.compile(r'<file name="([^"]+)">([\s\S]*?)</file>')
_SUMMARY_TAG_RE = re.compile(r"<summary>([\s\S]*?)</summary>", re.IGNORECASE)
_POSTER_FILE_RE = re.compile(r"^/poster-(v[1-4])-(4x5|9x16|16x9|1x1)\.tsx$", re.IGNORECASE)
_STAGE_EVENT_LABELS = {
    STAGE_BRAND_IDENTITY: "brand identity",
    STAGE_STARTER_BRAND: "brand identity foundation",
    STAGE_BRAND_OS: "Brand OS",
    STAGE_LOGO: "brand identity logo",
    STAGE_WEBSITE: "website",
    STAGE_POSTER_FLYERS: "poster and flyer pack",
    STAGE_VIDEO_BRIEFS: "video briefs",
    STAGE_VIDEO_RENDER: "starter video render",
    STAGE_NORMALIZE_INPUT: "input normalization",
    STAGE_QA_REVIEW: "final QA review",
}
