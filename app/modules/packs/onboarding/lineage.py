"""Artifact lineage helpers for onboarding status and repair flows."""

from __future__ import annotations

from app.modules.packs.onboarding.artifact_store import list_artifact_envelopes
from app.modules.packs.onboarding.artifacts import (
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    ARTIFACT_TYPE_BRAND_OS,
    ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
    ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
    ARTIFACT_TYPE_QA_REPORT,
    ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_RENDER_RESULT,
    ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
)

_ARTIFACT_DISPLAY_ORDER: tuple[str, ...] = (
    ARTIFACT_TYPE_NORMALIZED_BUSINESS_PROFILE,
    ARTIFACT_TYPE_BRAND_OS,
    ARTIFACT_TYPE_BRAND_IDENTITY_PROFILE,
    ARTIFACT_TYPE_WEBSITE_BLUEPRINT,
    ARTIFACT_TYPE_CREATIVE_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE,
    ARTIFACT_TYPE_VIDEO_RENDER_RESULT,
    ARTIFACT_TYPE_QA_REPORT,
)


def _artifact_summary(artifact_type: str, data: dict[str, object]) -> dict[str, object] | None:
    if artifact_type == ARTIFACT_TYPE_VIDEO_BRIEF_BUNDLE:
        scripts = data.get("voiceover_script")
        return {"script_count": len(scripts)} if isinstance(scripts, list) else None
    if artifact_type == ARTIFACT_TYPE_VIDEO_RENDER_RESULT:
        return {
            "rendered_count": int(data.get("rendered_count") or 0),
            "requested_count": int(data.get("requested_count") or 0),
        }
    if artifact_type == ARTIFACT_TYPE_QA_REPORT:
        summary = {
            "overall_status": data.get("overall_status"),
            "consistency_score": data.get("consistency_score"),
            "recommended_repair_stage": data.get("recommended_repair_stage"),
            "auto_repairable": data.get("auto_repairable"),
        }
        return {key: value for key, value in summary.items() if value not in (None, "")}
    return None


def build_artifact_lineage(pack) -> list[dict[str, object]]:
    envelopes = list_artifact_envelopes(pack)
    items: list[dict[str, object]] = []
    for artifact_type in _ARTIFACT_DISPLAY_ORDER:
        envelope = envelopes.get(artifact_type)
        if not envelope:
            continue
        summary = _artifact_summary(envelope.artifact_type, envelope.data)
        items.append(
            {
                "artifact_type": envelope.artifact_type,
                "version": envelope.version,
                "schema_version": envelope.schema_version,
                "source_stage": envelope.source_stage,
                "job_id": envelope.job_id,
                "input_fingerprint": envelope.input_fingerprint,
                "created_at": envelope.created_at,
                "updated_at": envelope.updated_at,
                "summary": summary,
            }
        )
    return items
