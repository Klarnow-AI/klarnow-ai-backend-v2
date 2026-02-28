"""Kling API client (official - api-singapore.klingai.com, JWT auth)."""

from __future__ import annotations

import time

import jwt
import requests

from app.core.config import get_settings


KLING_DEFAULT_BASE = "https://api-singapore.klingai.com"
KLING_MODEL = "kling-v2.6-pro"
KLING_MODE = "standard"


def _encode_jwt_token(ak: str, sk: str) -> str:
    """Generate JWT token per Kling API spec. Token valid 30 min (exp), starts -5s (nbf)."""
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5,
    }
    return jwt.encode(payload, sk, algorithm="HS256", headers=headers)


def _get_config() -> tuple[str, str, str]:
    s = get_settings()
    base = (s.kling_api_base_url or KLING_DEFAULT_BASE).rstrip("/")
    ak = s.kling_access_key or ""
    sk = s.kling_secret_key or ""
    return base, ak, sk


def _get_auth_header() -> str:
    """Build Authorization: Bearer <JWT> header."""
    _, ak, sk = _get_config()
    if not ak or not sk:
        raise ValueError("KLING_ACCESS_KEY and KLING_SECRET_KEY must be configured")
    token = _encode_jwt_token(ak, sk)
    return f"Bearer {token}"


def submit_text_to_video(
    prompt: str,
    duration: int = 10,
    aspect_ratio: str = "9:16",
) -> str:
    """Submit text-to-video job. Returns task_id. Raises if credentials missing or request fails."""
    base, ak, sk = _get_config()
    if not ak or not sk:
        raise ValueError("KLING_ACCESS_KEY and KLING_SECRET_KEY must be configured")

    auth = _get_auth_header()
    resp = requests.post(
        f"{base}/v1/videos/text2video",
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
        },
        json={
            "model": KLING_MODEL,
            "prompt": prompt[:4000],
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "mode": KLING_MODE,
            "negative_prompt": "blur, distort, low quality",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    task_id = data.get("task_id") or (data.get("data") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Kling API did not return task_id: {data}")
    return str(task_id)


def get_task_status(task_id: str) -> dict:
    """Get task status. Returns dict with status and video URL when complete."""
    base, ak, sk = _get_config()
    if not ak or not sk:
        raise ValueError("KLING_ACCESS_KEY and KLING_SECRET_KEY must be configured")

    auth = _get_auth_header()
    resp = requests.get(
        f"{base}/v1/videos/{task_id}",
        headers={"Authorization": auth},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def wait_for_video(
    task_id: str,
    poll_interval: int = 5,
    max_wait: int = 180,
) -> str:
    """Poll until video is ready. Returns video URL. Raises on failure or timeout."""
    elapsed = 0
    while elapsed < max_wait:
        status = get_task_status(task_id)
        s = str(status.get("status", "")).lower()
        if "succeed" in s or "complete" in s or "success" in s or s == "completed":
            data = status.get("data") or status
            v = data.get("video") or data.get("video_url") or data.get("url")
            if isinstance(v, dict):
                url = v.get("url") or v.get("video_url")
            else:
                url = v
            if url:
                return str(url)
            raise RuntimeError(f"Kling task completed but no video URL in response: {status}")
        if "fail" in s or "error" in s:
            msg = status.get("message") or status.get("error") or "Kling generation failed"
            raise RuntimeError(str(msg))
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise TimeoutError(f"Kling task {task_id} did not complete within {max_wait}s")


def download_video(url: str) -> bytes:
    """Download video bytes from URL."""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content
