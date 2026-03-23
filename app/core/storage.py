"""Storage: S3 upload/delete helpers."""

import logging
import threading
import time
from urllib.parse import quote, unquote, urlsplit

import requests

from app.core.config import get_settings

CDN_PROBE_TIMEOUT_SECONDS = 2
CDN_FAILURE_COOLDOWN_SECONDS = 300

logger = logging.getLogger(__name__)
_CDN_FAILURE_LOCK = threading.Lock()
_CDN_FAILURE_UNTIL_BY_BASE: dict[str, float] = {}


def storage_enabled() -> bool:
    s = get_settings()
    return bool(s.storage_bucket and s.storage_access_key_id)


def get_s3_client():
    import boto3
    s = get_settings()
    if not storage_enabled():
        return None, None
    client = boto3.client(
        "s3",
        region_name=s.storage_region,
        aws_access_key_id=s.storage_access_key_id,
        aws_secret_access_key=s.storage_secret_access_key,
    )
    return client, s.storage_bucket


def upload_file(
    key: str,
    body: bytes,
    content_type: str | None = None,
    *,
    cache_control: str | None = None,
) -> str | None:
    """Upload bytes to S3. Returns key on success, None if S3 not configured."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return None
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    if cache_control:
        extra["CacheControl"] = cache_control
    client.put_object(Bucket=bucket, Key=key, Body=body, **extra)
    return key


def delete_file(key: str) -> bool:
    """Delete object from S3. Returns True if deleted or S3 not configured."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return True
    client.delete_object(Bucket=bucket, Key=key)
    return True


def download_file(key: str) -> bytes | None:
    """Download bytes from S3. Returns None when unavailable or missing."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return None
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception:
        return None
    body = response.get("Body")
    if body is None:
        return None
    return body.read()


def get_presigned_url(key: str, expires_in: int = 3600) -> str | None:
    """Generate presigned GET URL for download."""
    client, bucket = get_s3_client()
    if not client or not bucket:
        return None
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
    )


def _build_cdn_url(cdn_base: str, key: str) -> str:
    encoded_key = "/".join(quote(part, safe="") for part in key.lstrip("/").split("/"))
    return f"{cdn_base.rstrip('/')}/{encoded_key}"


def _cdn_failure_active(cdn_base: str) -> bool:
    with _CDN_FAILURE_LOCK:
        failure_until = _CDN_FAILURE_UNTIL_BY_BASE.get(cdn_base, 0.0)
        if failure_until <= time.monotonic():
            _CDN_FAILURE_UNTIL_BY_BASE.pop(cdn_base, None)
            return False
        return True


def _set_cdn_failure_cooldown(cdn_base: str) -> None:
    with _CDN_FAILURE_LOCK:
        _CDN_FAILURE_UNTIL_BY_BASE[cdn_base] = time.monotonic() + CDN_FAILURE_COOLDOWN_SECONDS


def _cdn_url_available(url: str) -> bool:
    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=CDN_PROBE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("storage_cdn_probe_failed | url=%s | error=%s", url, exc)
        return False
    return response.status_code == 405 or 200 <= response.status_code < 400


def extract_storage_key(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None

    if raw.startswith("key:"):
        key = raw[4:].lstrip("/")
        return key or None

    cdn_base = (get_settings().storage_cdn_url or "").strip().rstrip("/")
    if not cdn_base or not raw.startswith(f"{cdn_base}/"):
        return None

    base_parts = urlsplit(cdn_base)
    value_parts = urlsplit(raw)
    if (
        value_parts.scheme != base_parts.scheme
        or value_parts.netloc != base_parts.netloc
        or not value_parts.path.startswith(f"{base_parts.path.rstrip('/')}/")
    ):
        return None

    encoded_key = value_parts.path[len(base_parts.path.rstrip("/")) + 1 :]
    key = "/".join(unquote(part) for part in encoded_key.split("/"))
    return key or None


def resolve_asset_reference(value: str | None, expires_in: int = 3600) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None

    key = extract_storage_key(raw)
    if not key:
        return raw

    return get_asset_url(key, expires_in=expires_in) or raw


def get_asset_url(key: str, expires_in: int = 3600) -> str | None:
    """Return a CDN/public URL when configured, otherwise fall back to a presigned URL."""
    if not key:
        return None

    s = get_settings()
    cdn_base = (s.storage_cdn_url or "").strip().rstrip("/")
    if cdn_base:
        cdn_url = _build_cdn_url(cdn_base, key)
        if _cdn_failure_active(cdn_base):
            return get_presigned_url(key, expires_in=expires_in)
        if _cdn_url_available(cdn_url):
            return cdn_url
        _set_cdn_failure_cooldown(cdn_base)
        logger.warning("storage_cdn_unavailable_falling_back_to_presigned | url=%s", cdn_url)

    return get_presigned_url(key, expires_in=expires_in)
