"""Cheap artifact persistence for onboarding runs."""

from __future__ import annotations

import json
from typing import Any

from app.modules.packs.onboarding.artifacts import ArtifactEnvelope, ArtifactModel, validate_artifact_model

ONBOARDING_ARTIFACTS_KEY = "_onboarding_artifacts"


def _answers_dict(pack: Any) -> dict[str, Any]:
    answers = getattr(pack, "onboarding_answers", None)
    return dict(answers) if isinstance(answers, dict) else {}


def _normalize_artifact_store(raw: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict):
        return {
            str(key): dict(value)
            for key, value in raw.items()
            if isinstance(value, dict)
        }
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return {}
        if isinstance(parsed, dict):
            return {
                str(key): dict(value)
                for key, value in parsed.items()
                if isinstance(value, dict)
            }
    return {}


def get_artifact_store(pack: Any) -> dict[str, dict[str, Any]]:
    answers = _answers_dict(pack)
    return _normalize_artifact_store(answers.get(ONBOARDING_ARTIFACTS_KEY))


def set_artifact_store(pack: Any, store: dict[str, Any]) -> None:
    answers = _answers_dict(pack)
    answers[ONBOARDING_ARTIFACTS_KEY] = {
        str(key): dict(value)
        for key, value in store.items()
        if isinstance(value, dict)
    }
    pack.onboarding_answers = answers


def get_artifact_envelope(pack: Any, artifact_type: str) -> ArtifactEnvelope | None:
    store = get_artifact_store(pack)
    raw = store.get(str(artifact_type))
    if not isinstance(raw, dict):
        return None
    try:
        return ArtifactEnvelope.model_validate(raw)
    except Exception:
        return None


def get_artifact(pack: Any, artifact_type: str) -> ArtifactModel | None:
    envelope = get_artifact_envelope(pack, artifact_type)
    if not envelope:
        return None
    try:
        return validate_artifact_model(artifact_type, envelope.data)
    except Exception:
        return None


def list_artifact_envelopes(pack: Any) -> dict[str, ArtifactEnvelope]:
    store = get_artifact_store(pack)
    envelopes: dict[str, ArtifactEnvelope] = {}
    for artifact_type in store:
        envelope = get_artifact_envelope(pack, artifact_type)
        if envelope:
            envelopes[artifact_type] = envelope
    return envelopes


def get_artifact_versions(pack: Any) -> dict[str, int]:
    return {
        artifact_type: envelope.version
        for artifact_type, envelope in list_artifact_envelopes(pack).items()
    }


def save_artifact(
    pack: Any,
    artifact_type: str,
    artifact: ArtifactModel | dict[str, Any],
    *,
    source_stage: str,
    timestamp: str,
    job_id: str | None = None,
    input_fingerprint: str | None = None,
) -> ArtifactEnvelope:
    validated = validate_artifact_model(artifact_type, artifact)
    next_data = validated.model_dump(mode="json")
    store = get_artifact_store(pack)
    previous = get_artifact_envelope(pack, artifact_type)
    if previous and previous.data == next_data:
        version = previous.version
        created_at = previous.created_at
    elif previous:
        version = previous.version + 1
        created_at = previous.created_at
    else:
        version = 1
        created_at = timestamp
    envelope = ArtifactEnvelope(
        artifact_type=artifact_type,
        version=version,
        source_stage=source_stage,
        job_id=str(job_id) if job_id else None,
        input_fingerprint=input_fingerprint,
        created_at=created_at,
        updated_at=timestamp,
        data=next_data,
    )
    store[str(artifact_type)] = envelope.model_dump(mode="json")
    set_artifact_store(pack, store)
    return envelope
