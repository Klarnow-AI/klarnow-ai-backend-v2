"""Image context indexing, embedding, and retrieval services."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.storage import get_presigned_url
from app.modules.creative.models import Asset
from app.modules.image_context.models import (
    EMBEDDING_DIMENSION,
    GlobalImageContextItem,
    ImageContextItem,
    ImageContextJob,
)
from app.modules.packs.services import get_pack_for_user
from app.modules.proof_vault.models import Proof

logger = get_logger("klarnow.image_context")

SOURCE_TYPE_PROOF = "proof"
SOURCE_TYPE_ASSET = "asset"
SOURCE_TYPE_GLOBAL = "global"
JOB_OPERATION_UPSERT = "upsert"
JOB_OPERATION_DELETE = "delete"
JOB_STATUSES_IN_FLIGHT = {"queued", "running"}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
}


def _looks_like_image_key(storage_key: str | None) -> bool:
    if not isinstance(storage_key, str) or not storage_key.strip():
        return False
    ext = Path(storage_key).suffix.lower()
    return ext in IMAGE_EXTENSIONS


def _guess_content_type(storage_key: str | None) -> str | None:
    if not storage_key:
        return None
    guessed, _ = mimetypes.guess_type(storage_key)
    return guessed


def _basename(storage_key: str | None) -> str | None:
    if not storage_key:
        return None
    name = os.path.basename(storage_key)
    return name or None


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    out: list[str] = []
    for tag in tags:
        cleaned = str(tag).strip()
        if cleaned:
            out.append(cleaned)
    return out


def _first_user_prompt(chat_messages: list[dict] | dict | None) -> str | None:
    if not isinstance(chat_messages, list):
        return None
    for row in chat_messages:
        if not isinstance(row, dict):
            continue
        if row.get("role") != "user":
            continue
        content = row.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return None


def _build_fallback_caption(source_name: str | None, metadata_json: dict[str, Any]) -> str:
    tags = metadata_json.get("tags")
    tags_text = ""
    if isinstance(tags, list) and tags:
        tags_text = ", ".join(str(tag).strip() for tag in tags if str(tag).strip())
    if source_name and tags_text:
        return f"{source_name}. Tags: {tags_text}."
    if source_name:
        return f"{source_name}."
    if tags_text:
        return f"Tags: {tags_text}."
    return "Image reference from library."


def _build_embedding_text(
    *,
    caption: str,
    source_type: str,
    source_name: str | None,
    metadata_json: dict[str, Any],
) -> str:
    lines = [f"Source type: {source_type}", f"Caption: {caption.strip()}"]
    if source_name:
        lines.append(f"Source name: {source_name}")

    tags = metadata_json.get("tags")
    if isinstance(tags, list) and tags:
        lines.append("Tags: " + ", ".join(str(tag).strip() for tag in tags if str(tag).strip()))

    asset_type = metadata_json.get("asset_type")
    if isinstance(asset_type, str) and asset_type.strip():
        lines.append(f"Asset type: {asset_type.strip()}")

    template_id = metadata_json.get("template_id")
    if isinstance(template_id, str) and template_id.strip():
        lines.append(f"Template: {template_id.strip()}")

    prompt = metadata_json.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        lines.append(f"Prompt intent: {prompt.strip()[:800]}")

    return "\n".join(lines)


def _openai_client() -> OpenAI | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _embed_text(
    client: OpenAI,
    model: str,
    text: str,
) -> list[float]:
    response = client.embeddings.create(model=model, input=text)
    if not response.data:
        raise ValueError("Embedding API returned no vectors")
    vector = response.data[0].embedding
    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(vector)}"
        )
    return vector


def _generate_caption_from_image(
    client: OpenAI,
    model: str,
    image_url: str,
    source_label: str,
) -> str | None:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You describe marketing reference images for retrieval. "
                    "Return one concise sentence focused on subject, style, text visible, and intent."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this image in one sentence for semantic retrieval. "
                            f"Source label: {source_label}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        max_tokens=120,
    )
    content = response.choices[0].message.content if response.choices else None
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def _upsert_item(
    db: Session,
    *,
    user_id: UUID,
    pack_id: UUID,
    source_type: str,
    source_id: UUID,
    source_storage_key: str | None,
    source_name: str | None,
    source_content_type: str | None,
    caption: str,
    metadata_json: dict[str, Any],
    embedding: list[float],
) -> None:
    item = (
        db.query(ImageContextItem)
        .filter(
            ImageContextItem.user_id == user_id,
            ImageContextItem.pack_id == pack_id,
            ImageContextItem.source_type == source_type,
            ImageContextItem.source_id == source_id,
        )
        .first()
    )
    if not item:
        item = ImageContextItem(
            user_id=user_id,
            pack_id=pack_id,
            source_type=source_type,
            source_id=source_id,
        )
        db.add(item)

    item.source_storage_key = source_storage_key
    item.source_name = source_name
    item.source_content_type = source_content_type
    item.caption = caption
    item.metadata_json = metadata_json
    item.embedding = embedding
    item.status = "ready"
    item.error_message = None
    db.flush()


def _delete_item_for_source(
    db: Session,
    *,
    user_id: UUID,
    pack_id: UUID,
    source_type: str,
    source_id: UUID,
) -> None:
    (
        db.query(ImageContextItem)
        .filter(
            ImageContextItem.user_id == user_id,
            ImageContextItem.pack_id == pack_id,
            ImageContextItem.source_type == source_type,
            ImageContextItem.source_id == source_id,
        )
        .delete(synchronize_session=False)
    )
    db.flush()


def enqueue_image_context_job(
    db: Session,
    *,
    user_id: UUID,
    pack_id: UUID,
    source_type: str,
    source_id: UUID,
    operation: str,
    payload: dict[str, Any] | None = None,
    max_attempts: int | None = None,
    commit: bool = True,
) -> ImageContextJob:
    settings = get_settings()

    normalized_source_type = source_type.strip().lower()
    if normalized_source_type not in {SOURCE_TYPE_PROOF, SOURCE_TYPE_ASSET}:
        raise ValueError("Unsupported source_type")

    normalized_operation = operation.strip().lower()
    if normalized_operation not in {JOB_OPERATION_UPSERT, JOB_OPERATION_DELETE}:
        raise ValueError("Unsupported image context job operation")

    existing = (
        db.query(ImageContextJob)
        .filter(
            ImageContextJob.user_id == user_id,
            ImageContextJob.pack_id == pack_id,
            ImageContextJob.source_type == normalized_source_type,
            ImageContextJob.source_id == source_id,
            ImageContextJob.operation == normalized_operation,
            ImageContextJob.status.in_(tuple(JOB_STATUSES_IN_FLIGHT)),
        )
        .order_by(ImageContextJob.created_at.desc())
        .first()
    )
    if existing:
        return existing

    job = ImageContextJob(
        user_id=user_id,
        pack_id=pack_id,
        source_type=normalized_source_type,
        source_id=source_id,
        operation=normalized_operation,
        status="queued",
        attempt=0,
        max_attempts=max(1, max_attempts or settings.image_context_job_max_attempts),
        payload=payload,
    )
    db.add(job)
    if commit:
        db.commit()
        db.refresh(job)
    else:
        db.flush()
    return job


def enqueue_pack_backfill_jobs(
    db: Session,
    *,
    user_id: UUID,
    pack_id: UUID,
    include_proofs: bool = True,
    include_assets: bool = True,
) -> dict[str, int]:
    if not get_pack_for_user(db, pack_id, user_id):
        raise ValueError("Pack not found")

    queued_proof_jobs = 0
    queued_asset_jobs = 0

    if include_proofs:
        proofs = db.query(Proof).filter(Proof.pack_id == pack_id).all()
        for proof in proofs:
            if not _looks_like_image_key(proof.file_key):
                continue
            enqueue_image_context_job(
                db,
                user_id=user_id,
                pack_id=pack_id,
                source_type=SOURCE_TYPE_PROOF,
                source_id=proof.id,
                operation=JOB_OPERATION_UPSERT,
                commit=False,
            )
            queued_proof_jobs += 1

    if include_assets:
        assets = db.query(Asset).filter(Asset.pack_id == pack_id).all()
        for asset in assets:
            if not _looks_like_image_key(asset.output_key):
                continue
            enqueue_image_context_job(
                db,
                user_id=user_id,
                pack_id=pack_id,
                source_type=SOURCE_TYPE_ASSET,
                source_id=asset.id,
                operation=JOB_OPERATION_UPSERT,
                commit=False,
            )
            queued_asset_jobs += 1

    db.commit()
    return {
        "queued_jobs": queued_proof_jobs + queued_asset_jobs,
        "queued_proof_jobs": queued_proof_jobs,
        "queued_asset_jobs": queued_asset_jobs,
    }


def _build_proof_index_payload(db: Session, job: ImageContextJob) -> dict[str, Any] | None:
    proof = (
        db.query(Proof)
        .filter(
            Proof.id == job.source_id,
            Proof.pack_id == job.pack_id,
        )
        .first()
    )
    if not proof:
        return None

    if not get_pack_for_user(db, job.pack_id, job.user_id):
        return None

    if not _looks_like_image_key(proof.file_key):
        return None

    source_name = _basename(proof.file_key)
    metadata_json: dict[str, Any] = {
        "tags": _normalize_tags(proof.tags),
        "proof_text": (proof.proof_text or "").strip()[:800] if proof.proof_text else None,
    }
    if metadata_json.get("proof_text") is None:
        metadata_json.pop("proof_text", None)

    return {
        "source_storage_key": proof.file_key,
        "source_name": source_name,
        "source_content_type": _guess_content_type(proof.file_key),
        "metadata_json": metadata_json,
    }


def _build_asset_index_payload(db: Session, job: ImageContextJob) -> dict[str, Any] | None:
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == job.source_id,
            Asset.pack_id == job.pack_id,
        )
        .first()
    )
    if not asset:
        return None

    if not get_pack_for_user(db, job.pack_id, job.user_id):
        return None

    if not _looks_like_image_key(asset.output_key):
        return None

    metadata_json: dict[str, Any] = {
        "asset_type": asset.type,
        "version": asset.version,
        "template_id": asset.template_id,
    }
    prompt = _first_user_prompt(asset.chat_messages)
    if prompt:
        metadata_json["prompt"] = prompt

    return {
        "source_storage_key": asset.output_key,
        "source_name": asset.name or _basename(asset.output_key),
        "source_content_type": _guess_content_type(asset.output_key),
        "metadata_json": metadata_json,
    }


def process_image_context_job(db: Session, job: ImageContextJob) -> None:
    settings = get_settings()

    if job.operation == JOB_OPERATION_DELETE:
        _delete_item_for_source(
            db,
            user_id=job.user_id,
            pack_id=job.pack_id,
            source_type=job.source_type,
            source_id=job.source_id,
        )
        return

    if job.operation != JOB_OPERATION_UPSERT:
        raise ValueError(f"Unknown operation: {job.operation}")

    if job.source_type == SOURCE_TYPE_PROOF:
        source_payload = _build_proof_index_payload(db, job)
    elif job.source_type == SOURCE_TYPE_ASSET:
        source_payload = _build_asset_index_payload(db, job)
    else:
        raise ValueError(f"Unknown source_type: {job.source_type}")

    if not source_payload:
        _delete_item_for_source(
            db,
            user_id=job.user_id,
            pack_id=job.pack_id,
            source_type=job.source_type,
            source_id=job.source_id,
        )
        return

    client = _openai_client()
    if not client:
        raise ValueError("OPENAI_API_KEY is required for image context indexing")

    source_storage_key = source_payload["source_storage_key"]
    source_name = source_payload.get("source_name")
    source_content_type = source_payload.get("source_content_type")
    metadata_json = source_payload.get("metadata_json") or {}

    caption = _build_fallback_caption(source_name, metadata_json)
    preview_url = get_presigned_url(
        source_storage_key,
        expires_in=max(60, settings.image_context_preview_url_ttl_seconds),
    )

    if preview_url:
        try:
            generated_caption = _generate_caption_from_image(
                client,
                settings.image_context_caption_model,
                preview_url,
                source_name or job.source_type,
            )
            if generated_caption:
                caption = generated_caption
        except Exception as e:
            logger.warning(
                "image_context_caption_generation_failed | job_id=%s | source_type=%s | error=%s",
                job.id,
                job.source_type,
                e,
            )

    embedding_text = _build_embedding_text(
        caption=caption,
        source_type=job.source_type,
        source_name=source_name,
        metadata_json=metadata_json,
    )
    embedding = _embed_text(
        client,
        settings.image_context_embedding_model,
        embedding_text,
    )

    _upsert_item(
        db,
        user_id=job.user_id,
        pack_id=job.pack_id,
        source_type=job.source_type,
        source_id=job.source_id,
        source_storage_key=source_storage_key,
        source_name=source_name,
        source_content_type=source_content_type,
        caption=caption,
        metadata_json=metadata_json,
        embedding=embedding,
    )


def retrieve_pack_image_context(
    db: Session,
    *,
    user_id: UUID,
    pack_id: UUID,
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
    max_image_urls: int = 3,
) -> dict[str, Any]:
    settings = get_settings()

    if not settings.image_context_enabled:
        return {"items": [], "references": [], "context_text": "", "image_urls": []}

    trimmed_query = query.strip()
    if not trimmed_query:
        return {"items": [], "references": [], "context_text": "", "image_urls": []}

    if not get_pack_for_user(db, pack_id, user_id):
        raise ValueError("Pack not found")

    client = _openai_client()
    if not client:
        logger.warning("image_context_retrieve_skip_no_openai_key")
        return {"items": [], "references": [], "context_text": "", "image_urls": []}

    query_embedding = _embed_text(
        client,
        settings.image_context_embedding_model,
        trimmed_query,
    )

    effective_top_k = max(1, top_k or settings.image_context_top_k)
    effective_min_score = (
        float(min_score)
        if min_score is not None
        else float(settings.image_context_min_score)
    )

    score_expr = (1 - ImageContextItem.embedding.cosine_distance(query_embedding)).label("score")

    rows = (
        db.query(ImageContextItem, score_expr)
        .filter(
            ImageContextItem.user_id == user_id,
            ImageContextItem.pack_id == pack_id,
            ImageContextItem.status == "ready",
            ImageContextItem.embedding.is_not(None),
            score_expr >= effective_min_score,
        )
        .order_by(score_expr.desc())
        .limit(effective_top_k)
        .all()
    )

    items: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    context_lines: list[str] = []
    image_urls: list[str] = []

    for item, score in rows:
        preview_url = None
        if item.source_storage_key:
            preview_url = get_presigned_url(
                item.source_storage_key,
                expires_in=max(60, settings.image_context_preview_url_ttl_seconds),
            )

        numeric_score = round(float(score or 0.0), 4)
        caption = (item.caption or "Image reference").strip()
        metadata_json = item.metadata_json if isinstance(item.metadata_json, dict) else None

        items.append(
            {
                "id": item.id,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "source_name": item.source_name,
                "caption": caption,
                "metadata_json": metadata_json,
                "score": numeric_score,
                "preview_url": preview_url,
            }
        )
        references.append(
            {
                "chunk_id": f"img-{item.id}",
                "score": numeric_score,
                "excerpt": caption[:280],
            }
        )
        context_lines.append(f"- [{item.source_type}] {caption}")

        if preview_url and preview_url not in image_urls and len(image_urls) < max(1, max_image_urls):
            image_urls.append(preview_url)

    context_text = "\n".join(context_lines)
    return {
        "items": items,
        "references": references,
        "context_text": context_text,
        "image_urls": image_urls,
    }


def _upsert_global_item(
    db: Session,
    *,
    source_storage_key: str,
    source_name: str | None,
    source_content_type: str | None,
    caption: str,
    metadata_json: dict[str, Any],
    embedding: list[float],
) -> GlobalImageContextItem:
    item = (
        db.query(GlobalImageContextItem)
        .filter(GlobalImageContextItem.source_storage_key == source_storage_key)
        .first()
    )
    if not item:
        item = GlobalImageContextItem(source_storage_key=source_storage_key)
        db.add(item)

    item.source_name = source_name
    item.source_content_type = source_content_type
    item.caption = caption
    item.metadata_json = metadata_json
    item.embedding = embedding
    item.status = "ready"
    item.error_message = None
    db.commit()
    db.refresh(item)
    return item


def upsert_global_image_context_item(
    db: Session,
    *,
    source_storage_key: str,
    source_name: str | None = None,
    source_content_type: str | None = None,
    caption: str | None = None,
    tags: list[str] | None = None,
) -> GlobalImageContextItem:
    settings = get_settings()
    client = _openai_client()
    if not client:
        raise ValueError("OPENAI_API_KEY is required for image context indexing")

    metadata_json: dict[str, Any] = {}
    normalized_tags = _normalize_tags(tags)
    if normalized_tags:
        metadata_json["tags"] = normalized_tags

    has_caption_override = isinstance(caption, str) and bool(caption.strip())
    resolved_caption = (caption or "").strip() or _build_fallback_caption(
        source_name, metadata_json
    )
    preview_url = get_presigned_url(
        source_storage_key,
        expires_in=max(60, settings.image_context_preview_url_ttl_seconds),
    )

    if preview_url and not has_caption_override:
        try:
            generated_caption = _generate_caption_from_image(
                client,
                settings.image_context_caption_model,
                preview_url,
                source_name or SOURCE_TYPE_GLOBAL,
            )
            if generated_caption:
                resolved_caption = generated_caption
        except Exception as e:
            logger.warning(
                "global_image_context_caption_generation_failed | source=%s | error=%s",
                source_storage_key,
                e,
            )

    embedding_text = _build_embedding_text(
        caption=resolved_caption,
        source_type=SOURCE_TYPE_GLOBAL,
        source_name=source_name,
        metadata_json=metadata_json,
    )
    embedding = _embed_text(
        client,
        settings.image_context_embedding_model,
        embedding_text,
    )

    return _upsert_global_item(
        db,
        source_storage_key=source_storage_key,
        source_name=source_name,
        source_content_type=source_content_type,
        caption=resolved_caption,
        metadata_json=metadata_json,
        embedding=embedding,
    )


def retrieve_global_image_context(
    db: Session,
    *,
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
    max_image_urls: int = 3,
) -> dict[str, Any]:
    settings = get_settings()

    if not settings.image_context_enabled:
        return {"items": [], "references": [], "context_text": "", "image_urls": []}

    trimmed_query = query.strip()
    if not trimmed_query:
        return {"items": [], "references": [], "context_text": "", "image_urls": []}

    client = _openai_client()
    if not client:
        logger.warning("global_image_context_retrieve_skip_no_openai_key")
        return {"items": [], "references": [], "context_text": "", "image_urls": []}

    query_embedding = _embed_text(
        client,
        settings.image_context_embedding_model,
        trimmed_query,
    )
    effective_top_k = max(1, top_k or settings.image_context_top_k)
    effective_min_score = (
        float(min_score)
        if min_score is not None
        else float(settings.image_context_min_score)
    )

    score_expr = (
        1 - GlobalImageContextItem.embedding.cosine_distance(query_embedding)
    ).label("score")

    rows = (
        db.query(GlobalImageContextItem, score_expr)
        .filter(
            GlobalImageContextItem.status == "ready",
            GlobalImageContextItem.embedding.is_not(None),
            score_expr >= effective_min_score,
        )
        .order_by(score_expr.desc())
        .limit(effective_top_k)
        .all()
    )

    items: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    context_lines: list[str] = []
    image_urls: list[str] = []

    for item, score in rows:
        preview_url = get_presigned_url(
            item.source_storage_key,
            expires_in=max(60, settings.image_context_preview_url_ttl_seconds),
        )
        numeric_score = round(float(score or 0.0), 4)
        caption = (item.caption or "Image reference").strip()
        metadata_json = item.metadata_json if isinstance(item.metadata_json, dict) else None

        items.append(
            {
                "id": item.id,
                "source_name": item.source_name,
                "caption": caption,
                "metadata_json": metadata_json,
                "score": numeric_score,
                "preview_url": preview_url,
            }
        )
        references.append(
            {
                "chunk_id": f"global-img-{item.id}",
                "score": numeric_score,
                "excerpt": caption[:280],
            }
        )
        context_lines.append(f"- [global] {caption}")

        if preview_url and preview_url not in image_urls and len(image_urls) < max(1, max_image_urls):
            image_urls.append(preview_url)

    return {
        "items": items,
        "references": references,
        "context_text": "\n".join(context_lines),
        "image_urls": image_urls,
    }
