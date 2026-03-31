"""Helpers for parsing and storing onboarding-generated website and poster assets."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .constants import (
    _AUTO_POSTER_QUEUE_CONFIG,
    _AUTO_POSTER_SIZE_IDS,
    _DEFAULT_BUILDER_APP,
    _DEFAULT_BUILDER_APP_MARKER,
    _FILE_TAG_RE,
    _POSTER_FILE_RE,
    _SUMMARY_TAG_RE,
)


async def _collect_async_stream_text(stream_factory_coro) -> str:
    stream = await stream_factory_coro
    parts: list[str] = []
    async for chunk in stream:
        if chunk:
            parts.append(chunk)
    return "".join(parts)


def _collect_stream_text(stream_factory_coro) -> str:
    return asyncio.run(_collect_async_stream_text(stream_factory_coro))


def _parse_generated_files(text: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for match in _FILE_TAG_RE.finditer(text or ""):
        name = match.group(1).strip()
        normalized_name = name if name.startswith("/") else f"/{name}"
        files[normalized_name] = match.group(2).strip()
    return files


def _parse_generation_summary(text: str) -> str | None:
    match = _SUMMARY_TAG_RE.search(text or "")
    if not match:
        return None
    summary = match.group(1).strip()
    return summary or None


def _default_builder_files() -> dict[str, str]:
    return {"/App.tsx": _DEFAULT_BUILDER_APP}


def _is_default_builder_files(files: dict[str, Any] | None) -> bool:
    if not isinstance(files, dict) or len(files) != 1:
        return False
    app_code = str(files.get("/App.tsx") or files.get("App.tsx") or "")
    return _DEFAULT_BUILDER_APP_MARKER in app_code


def _has_generated_website_project(project: Any) -> bool:
    files = project.files if isinstance(getattr(project, "files", None), dict) else {}
    if not files:
        return False
    app_code = str(files.get("/App.tsx") or files.get("App.tsx") or "").strip()
    return bool(app_code) and _DEFAULT_BUILDER_APP_MARKER not in app_code


def _extract_poster_template_id(name: str) -> str | None:
    match = _POSTER_FILE_RE.match(name.strip())
    if not match:
        return None
    return match.group(2).lower()


def _is_background_generation_messages(messages: Any) -> bool:
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        meta = message.get("meta")
        if isinstance(meta, dict) and meta.get("kind") == "background_generation":
            return True
    return False


def _build_auto_generation_messages(slot_id: str) -> list[dict[str, Any]]:
    slot_map = {slot: (label, description) for slot, label, description in _AUTO_POSTER_QUEUE_CONFIG}
    label, description = slot_map.get(slot_id, ("Starter concept", "Background task"))
    return [
        {
            "role": "assistant",
            "content": f"{label} generated automatically.",
            "meta": {
                "kind": "background_generation",
                "label": label,
                "taskLabel": description,
                "modeLabel": "Starter poster pack",
            },
        }
    ]


def _expected_auto_poster_names() -> set[str]:
    return {
        f"/poster-{slot_id}-{size_id}.tsx"
        for slot_id, _, _ in _AUTO_POSTER_QUEUE_CONFIG
        for size_id in _AUTO_POSTER_SIZE_IDS
    }


def _count_existing_auto_posters(db: Session, pack_id: UUID) -> int:
    from app.modules.creative.services import list_assets_for_pack

    expected_names = _expected_auto_poster_names()
    assets = list_assets_for_pack(db, pack_id)
    names = {
        str(asset.name)
        for asset in assets
        if getattr(asset, "type", None) in {"poster", "flyer"}
        and isinstance(getattr(asset, "source_code", None), str)
        and str(getattr(asset, "name", "") or "") in expected_names
        and _is_background_generation_messages(getattr(asset, "chat_messages", None))
    }
    return len(names)

