"""Storage: PocketBase upload/delete helpers."""

import asyncio
import logging
import mimetypes
import time
from pathlib import PurePosixPath

import httpx
import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TOKEN_LOCK = asyncio.Lock()
_cached_token: str | None = None
_token_expires_at: float = 0.0
_TOKEN_TTL_SECONDS = 43200  # 12 hours


def storage_enabled() -> bool:
    return bool(get_settings().pocketbase_url)


def _pb_base() -> str:
    return get_settings().pocketbase_url.rstrip("/")


async def _get_pb_token() -> str | None:
    global _cached_token, _token_expires_at
    s = get_settings()
    if not s.pocketbase_url:
        return None
    async with _TOKEN_LOCK:
        if _cached_token and time.monotonic() < _token_expires_at:
            return _cached_token
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{_pb_base()}/api/collections/_superusers/auth-with-password",
                    json={"identity": s.pocketbase_admin_email, "password": s.pocketbase_admin_password},
                )
            resp.raise_for_status()
            _cached_token = resp.json()["token"]
            _token_expires_at = time.monotonic() + _TOKEN_TTL_SECONDS
            return _cached_token
        except Exception as exc:
            logger.error("pocketbase_auth_failed | error=%s", exc)
            return None


def _parse_key(key: str) -> tuple[str, str] | tuple[None, None]:
    """Parse '{record_id}/{filename}' → (record_id, filename)."""
    parts = key.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None
    return parts[0], parts[1]


async def upload_file(
    key: str,
    body: bytes,
    content_type: str | None = None,
    *,
    cache_control: str | None = None,  # unused in PocketBase, kept for interface compat
) -> str | None:
    """Upload bytes to PocketBase. Returns '{record_id}/{filename}' on success."""
    if not storage_enabled():
        return None
    token = await _get_pb_token()
    if not token:
        return None

    filename = PurePosixPath(key).name or "file"
    ct = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{_pb_base()}/api/collections/storage_files/records",
                headers={"Authorization": token},
                files={"file": (filename, body, ct)},
                data={"path_key": key},
            )
        resp.raise_for_status()
        record = resp.json()
        return f"{record['id']}/{record['file']}"
    except Exception as exc:
        logger.error("pocketbase_upload_failed | key=%s | error=%s", key, exc)
        return None


async def delete_file(key: str) -> bool:
    """Delete record from PocketBase. Returns True if deleted or storage not configured."""
    if not storage_enabled():
        return True
    token = await _get_pb_token()
    if not token:
        return False
    record_id, _ = _parse_key(key)
    if not record_id:
        logger.warning("pocketbase_delete_skipped_bad_key | key=%s", key)
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{_pb_base()}/api/collections/storage_files/records/{record_id}",
                headers={"Authorization": token},
            )
        return resp.status_code in (200, 204, 404)
    except Exception as exc:
        logger.error("pocketbase_delete_failed | key=%s | error=%s", key, exc)
        return False


def download_file(key: str) -> bytes | None:
    """Download bytes from PocketBase. Returns None when unavailable or missing."""
    if not storage_enabled():
        return None
    record_id, filename = _parse_key(key)
    if not record_id:
        return None
    try:
        resp = requests.get(
            f"{_pb_base()}/api/files/storage_files/{record_id}/{filename}",
            timeout=60,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        logger.error("pocketbase_download_failed | key=%s | error=%s", key, exc)
        return None


def get_asset_url(key: str, expires_in: int = 3600) -> str | None:
    """Return a public PocketBase file URL. expires_in is unused (PocketBase URLs don't expire)."""
    if not key or not storage_enabled():
        return None
    record_id, filename = _parse_key(key)
    if not record_id:
        return None
    return f"{_pb_base()}/api/files/storage_files/{record_id}/{filename}"


def get_presigned_url(key: str, expires_in: int = 3600) -> str | None:
    """PocketBase files are public — alias for get_asset_url."""
    return get_asset_url(key)


def extract_storage_key(value: str | None) -> str | None:
    """Extract a storage key from a stored value or PocketBase file URL."""
    raw = (value or "").strip()
    if not raw:
        return None

    if raw.startswith("key:"):
        key = raw[4:].lstrip("/")
        return key or None

    # Handle PocketBase file URLs: {pb_base}/api/files/storage_files/{record_id}/{filename}
    pb_prefix = f"{_pb_base()}/api/files/storage_files/"
    if raw.startswith(pb_prefix):
        remainder = raw[len(pb_prefix):]
        return remainder or None

    return None


def resolve_asset_reference(value: str | None, expires_in: int = 3600) -> str | None:
    """Resolve a stored value (key: prefix, PocketBase URL, or bare URL) to a usable URL."""
    raw = (value or "").strip()
    if not raw:
        return None
    key = extract_storage_key(raw)
    if not key:
        return raw
    return get_asset_url(key) or raw
