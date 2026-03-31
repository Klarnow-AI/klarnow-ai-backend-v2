"""Onboarding job state normalization, aggregation, and event helpers."""

from __future__ import annotations

from typing import Any

from app.modules.packs.models import Pack

from .common import _iso_now
from .constants import (
    ONBOARDING_JOB_EVENTS_MAX,
    ONBOARDING_JOB_KEY,
    ONBOARDING_JOB_MAX_ATTEMPTS,
    ONBOARDING_JOB_STAGES,
    PUBLIC_ONBOARDING_STAGE_GROUPS,
    PUBLIC_STAGE_ALIASES,
    STAGE_BRAND_IDENTITY,
    STAGE_LOGO,
    STAGE_STARTER_BRAND,
    _STAGE_EVENT_LABELS,
)


def _default_stage_state() -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "last_error": None,
        "data": {},
    }


def _default_job_stages() -> dict[str, dict[str, Any]]:
    return {stage: _default_stage_state() for stage in ONBOARDING_JOB_STAGES}


def _default_job_events() -> list[dict[str, Any]]:
    return []


def _normalize_stage_state(raw: Any) -> dict[str, Any]:
    state = _default_stage_state()
    if isinstance(raw, dict):
        if raw.get("status"):
            state["status"] = str(raw["status"])
        state["started_at"] = raw.get("started_at")
        state["completed_at"] = raw.get("completed_at")
        state["last_error"] = raw.get("last_error")
        if isinstance(raw.get("data"), dict):
            state["data"] = dict(raw["data"])
    return state


def _normalize_job_event(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    timestamp = str(raw.get("timestamp") or "").strip()
    message = str(raw.get("message") or "").strip()
    if not timestamp or not message:
        return None
    level = str(raw.get("level") or "info").strip() or "info"
    stage = raw.get("stage")
    normalized_stage = str(stage).strip() if stage else None
    return {
        "timestamp": timestamp,
        "level": level[:32],
        "message": message[:1000],
        "stage": normalized_stage[:64] if normalized_stage else None,
    }


def _normalize_internal_stage_name(stage_name: Any) -> str | None:
    if not stage_name:
        return None
    normalized = str(stage_name).strip()
    if normalized in {STAGE_STARTER_BRAND, STAGE_LOGO}:
        return STAGE_BRAND_IDENTITY
    return normalized or None


def _normalize_job_data(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    normalized = dict(raw)
    normalized["job_id"] = str(raw.get("job_id") or "")
    normalized["status"] = str(raw.get("status") or "queued")
    normalized["input_fingerprint"] = str(raw.get("input_fingerprint") or "")
    normalized["attempt"] = int(raw.get("attempt") or 0)
    normalized["max_attempts"] = int(raw.get("max_attempts") or ONBOARDING_JOB_MAX_ATTEMPTS)
    normalized["queued_at"] = raw.get("queued_at")
    normalized["started_at"] = raw.get("started_at")
    normalized["completed_at"] = raw.get("completed_at")
    normalized["last_error"] = raw.get("last_error")
    normalized["pause_requested"] = bool(raw.get("pause_requested") or False)
    normalized["paused_at"] = raw.get("paused_at")
    normalized["current_stage"] = _normalize_internal_stage_name(raw.get("current_stage"))
    raw_stages = raw.get("stages") if isinstance(raw.get("stages"), dict) else {}
    normalized["stages"] = {
        stage: _normalize_stage_state(_resolve_raw_stage_state(raw_stages, stage))
        for stage in ONBOARDING_JOB_STAGES
    }
    raw_events = raw.get("events") if isinstance(raw.get("events"), list) else []
    normalized["events"] = [
        event
        for event in (_normalize_job_event(item) for item in raw_events[-ONBOARDING_JOB_EVENTS_MAX:])
        if event is not None
    ]
    return normalized


def _get_job_data(pack: Pack) -> dict[str, Any] | None:
    answers = pack.onboarding_answers or {}
    return _normalize_job_data(answers.get(ONBOARDING_JOB_KEY))


def _set_job_data(pack: Pack, job_data: dict[str, Any]) -> None:
    answers = dict(pack.onboarding_answers or {})
    answers[ONBOARDING_JOB_KEY] = _normalize_job_data(job_data)
    pack.onboarding_answers = answers


def _get_cached_fingerprint(pack: Pack, key: str) -> str:
    answers = pack.onboarding_answers or {}
    return str(answers.get(key) or "").strip()


def _public_stage_summary(stage_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": stage_state.get("status"),
        "started_at": stage_state.get("started_at"),
        "completed_at": stage_state.get("completed_at"),
        "last_error": stage_state.get("last_error"),
    }


def _aggregate_stage_states(stage_states: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_stage_state(state) for state in stage_states]
    if not normalized:
        return _default_stage_state()

    statuses = [str(state.get("status") or "pending") for state in normalized]
    started_at = min(
        (str(state["started_at"]) for state in normalized if state.get("started_at")),
        default=None,
    )
    completed_at = max(
        (str(state["completed_at"]) for state in normalized if state.get("completed_at")),
        default=None,
    )
    last_error = next(
        (state.get("last_error") for state in reversed(normalized) if state.get("last_error")),
        None,
    )

    if any(status == "failed" for status in statuses):
        aggregate_status = "failed"
        completed_at = None
    elif any(status == "running" for status in statuses):
        aggregate_status = "running"
        completed_at = None
    elif all(status in {"completed", "skipped"} for status in statuses):
        aggregate_status = "completed"
    elif any(status in {"completed", "skipped"} for status in statuses):
        aggregate_status = "running"
        completed_at = None
    else:
        aggregate_status = "pending"
        completed_at = None

    return {
        "status": aggregate_status,
        "started_at": started_at,
        "completed_at": completed_at,
        "last_error": last_error,
        "data": {},
    }


def _resolve_raw_stage_state(raw_stages: dict[str, Any], stage_name: str) -> Any:
    if stage_name != STAGE_BRAND_IDENTITY or stage_name in raw_stages:
        return raw_stages.get(stage_name)
    legacy_states = [raw_stages.get(STAGE_STARTER_BRAND), raw_stages.get(STAGE_LOGO)]
    if any(state is not None for state in legacy_states):
        return _aggregate_stage_states(legacy_states)
    return None


def _build_public_job_stages(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages = job.get("stages") if isinstance(job.get("stages"), dict) else {}
    return {
        public_stage_name: _aggregate_stage_states(
            [stages.get(stage_name) or _default_stage_state() for stage_name in internal_stage_names]
        )
        for public_stage_name, internal_stage_names in PUBLIC_ONBOARDING_STAGE_GROUPS
    }


def _map_internal_stage_to_public(stage_name: Any) -> str | None:
    if not stage_name:
        return None
    return PUBLIC_STAGE_ALIASES.get(str(stage_name))


def _stage_event_label(stage_name: str | None) -> str | None:
    if not stage_name:
        return None
    return _STAGE_EVENT_LABELS.get(stage_name, str(stage_name).replace("_", " "))


def _append_job_event(
    job: dict[str, Any],
    message: str,
    *,
    stage_name: str | None = None,
    level: str = "info",
) -> None:
    text = str(message or "").strip()
    if not text:
        return
    events = job.get("events") if isinstance(job.get("events"), list) else _default_job_events()
    events.append(
        {
            "timestamp": _iso_now(),
            "level": str(level or "info").strip()[:32] or "info",
            "message": text[:1000],
            "stage": _map_internal_stage_to_public(stage_name) if stage_name else None,
        }
    )
    job["events"] = events[-ONBOARDING_JOB_EVENTS_MAX:]


def _set_stage_state(
    job: dict[str, Any],
    stage_name: str,
    status: str,
    *,
    error: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    stages = job.get("stages") if isinstance(job.get("stages"), dict) else _default_job_stages()
    stage = _normalize_stage_state(stages.get(stage_name))
    previous_status = str(stage.get("status") or "pending")
    if status == "running" and not stage.get("started_at"):
        stage["started_at"] = _iso_now()
    if status in {"completed", "skipped"}:
        stage["completed_at"] = _iso_now()
        stage["last_error"] = None
    elif error is not None:
        stage["last_error"] = error[:2000]
    elif status == "running":
        stage["last_error"] = None
    stage["status"] = status
    if data:
        stage["data"].update(data)
    stages[stage_name] = stage
    job["stages"] = stages
    job["current_stage"] = stage_name if status == "running" else None

    stage_label = _stage_event_label(stage_name)
    if status == "running" and previous_status != "running" and stage_label:
        _append_job_event(job, f"Started {stage_label}.", stage_name=stage_name)
    elif status == "completed" and previous_status != "completed" and stage_label:
        _append_job_event(job, f"Completed {stage_label}.", stage_name=stage_name)
    elif status == "skipped" and previous_status != "skipped" and stage_label:
        _append_job_event(job, f"Skipped {stage_label}.", stage_name=stage_name)


def _pause_job(
    job: dict[str, Any],
    *,
    message: str,
    log_event: bool = True,
) -> None:
    job["status"] = "paused"
    job["pause_requested"] = False
    job["paused_at"] = _iso_now()
    job["current_stage"] = None
    job["last_error"] = None
    if log_event:
        _append_job_event(job, message)
