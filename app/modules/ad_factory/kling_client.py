"""Kling API client (official - api-singapore.klingai.com, JWT auth)."""

from __future__ import annotations

import logging
import time
from typing import Any

import jwt
import requests

from app.core.errors import BadGatewayError
from app.core.config import get_settings


KLING_DEFAULT_BASE = "https://api-singapore.klingai.com"
KLING_TEXT_TO_VIDEO_MODEL = "kling-v2-6"
KLING_TEXT_TO_VIDEO_MODE = "pro"
KLING_TEXT_TO_VIDEO_ENDPOINT = "/v1/videos/text2video"
KLING_LEGACY_STATUS_ENDPOINT = "/v1/videos"
KLING_ALLOWED_DURATIONS = {5, 10}
KLING_ALLOWED_ASPECT_RATIOS = {"16:9", "9:16", "1:1"}
KLING_MAX_PROMPT_CHARS = 2500

logger = logging.getLogger(__name__)


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


def _build_text_to_video_payload(
    prompt: str,
    duration: int,
    aspect_ratio: str,
) -> dict[str, str]:
    prompt_text = prompt.strip()
    if not prompt_text:
        raise ValueError("Render prompt is empty")
    if duration not in KLING_ALLOWED_DURATIONS:
        raise ValueError("Kling text-to-video duration must be 5 or 10 seconds")
    if aspect_ratio not in KLING_ALLOWED_ASPECT_RATIOS:
        raise ValueError("Kling aspect ratio must be one of 16:9, 9:16, or 1:1")

    return {
        "model_name": KLING_TEXT_TO_VIDEO_MODEL,
        "mode": KLING_TEXT_TO_VIDEO_MODE,
        "prompt": prompt_text[:KLING_MAX_PROMPT_CHARS],
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
        "sound": "off",
    }


def _response_payload(resp: requests.Response) -> dict[str, Any] | str | None:
    try:
        payload = resp.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        return payload

    text = resp.text.strip()
    return text[:1000] if text else None


def _provider_message(payload: dict[str, Any] | str | None) -> str:
    if isinstance(payload, dict):
        for key in ("message", "error", "msg"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("message", "error", "msg"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return ""


def _request_context(payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if not payload:
        return None
    context = {key: value for key, value in payload.items() if key != "prompt"}
    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        context["prompt_chars"] = len(prompt)
    return context


def _raise_kling_http_error(
    action: str,
    resp: requests.Response,
    payload: dict[str, Any] | None = None,
) -> None:
    provider_payload = _response_payload(resp)
    provider_message = _provider_message(provider_payload)
    request_context = _request_context(payload)

    logger.error(
        "Kling %s failed: status=%s response=%s request=%s",
        action,
        resp.status_code,
        provider_payload,
        request_context,
    )

    data: dict[str, Any] = {
        "provider": "kling",
        "provider_status": resp.status_code,
    }
    if provider_payload is not None:
        data["provider_response"] = provider_payload
    if request_context is not None:
        data["request"] = request_context

    if 400 <= resp.status_code < 500:
        message = "Kling rejected the render request"
    else:
        message = f"Kling {action} failed"
    if provider_message:
        message = f"{message}: {provider_message}"

    raise BadGatewayError(message, data=data)


def _extract_video_url(payload: dict[str, Any]) -> str | None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    task_result = data.get("task_result") if isinstance(data.get("task_result"), dict) else None
    videos = task_result.get("videos") if isinstance(task_result, dict) else None
    if isinstance(videos, list):
        for item in videos:
            if isinstance(item, dict):
                url = item.get("url") or item.get("video_url")
                if url:
                    return str(url)

    video = data.get("video") or data.get("video_url") or data.get("url")
    if isinstance(video, dict):
        url = video.get("url") or video.get("video_url")
        return str(url) if url else None
    if isinstance(video, str) and video:
        return video
    return None


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
    payload = _build_text_to_video_payload(
        prompt=prompt,
        duration=duration,
        aspect_ratio=aspect_ratio,
    )
    try:
        resp = requests.post(
            f"{base}{KLING_TEXT_TO_VIDEO_ENDPOINT}",
            headers={
                "Authorization": auth,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.exception("Failed to reach Kling for text-to-video submission")
        raise BadGatewayError("Failed to reach Kling", data={"provider": "kling"}) from exc

    if not resp.ok:
        _raise_kling_http_error("text-to-video request", resp, payload)

    try:
        data = resp.json()
    except ValueError as exc:
        logger.error("Kling create-task response was not valid JSON: %s", resp.text)
        raise BadGatewayError(
            "Kling returned an invalid create-task response",
            data={"provider": "kling"},
        ) from exc

    task_id = data.get("task_id") or (data.get("data") or {}).get("task_id")
    if not task_id:
        raise BadGatewayError(
            "Kling did not return a task id",
            data={"provider": "kling", "provider_response": data},
        )
    return str(task_id)


def get_task_status(task_id: str) -> dict:
    """Get task status. Returns dict with status and video URL when complete."""
    base, ak, sk = _get_config()
    if not ak or not sk:
        raise ValueError("KLING_ACCESS_KEY and KLING_SECRET_KEY must be configured")

    auth = _get_auth_header()
    primary_url = f"{base}{KLING_TEXT_TO_VIDEO_ENDPOINT}/{task_id}"
    legacy_url = f"{base}{KLING_LEGACY_STATUS_ENDPOINT}/{task_id}"
    try:
        resp = requests.get(
            primary_url,
            headers={"Authorization": auth},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.exception("Failed to query Kling task status")
        raise BadGatewayError(
            "Failed to query Kling task status",
            data={"provider": "kling", "task_id": task_id},
        ) from exc

    if resp.status_code in {404, 405}:
        try:
            resp = requests.get(
                legacy_url,
                headers={"Authorization": auth},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to query Kling task status via legacy endpoint")
            raise BadGatewayError(
                "Failed to query Kling task status",
                data={"provider": "kling", "task_id": task_id},
            ) from exc

    if not resp.ok:
        _raise_kling_http_error("status query", resp, {"task_id": task_id})

    try:
        return resp.json()
    except ValueError as exc:
        logger.error("Kling status response was not valid JSON: %s", resp.text)
        raise BadGatewayError(
            "Kling returned an invalid status response",
            data={"provider": "kling", "task_id": task_id},
        ) from exc


def wait_for_video(
    task_id: str,
    poll_interval: int = 5,
    max_wait: int = 180,
) -> str:
    """Poll until video is ready. Returns video URL. Raises on failure or timeout."""
    elapsed = 0
    while elapsed < max_wait:
        status = get_task_status(task_id)
        data = status.get("data") if isinstance(status.get("data"), dict) else status
        s = str(data.get("task_status") or data.get("status") or status.get("status") or "").lower()
        if "succeed" in s or "complete" in s or "success" in s or s == "completed":
            url = _extract_video_url(status)
            if url:
                return str(url)
            raise BadGatewayError(
                "Kling task completed without a video URL",
                data={"provider": "kling", "task_id": task_id, "provider_response": status},
            )
        if "fail" in s or "error" in s:
            msg = (
                data.get("task_status_msg")
                or data.get("message")
                or status.get("message")
                or data.get("error")
                or "Kling generation failed"
            )
            raise BadGatewayError(
                str(msg),
                data={"provider": "kling", "task_id": task_id, "provider_response": status},
            )
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise BadGatewayError(
        f"Kling task {task_id} did not complete within {max_wait}s",
        data={"provider": "kling", "task_id": task_id},
    )


def download_video(url: str) -> bytes:
    """Download video bytes from URL."""
    try:
        resp = requests.get(url, timeout=120)
    except requests.RequestException as exc:
        logger.exception("Failed to download Kling video")
        raise BadGatewayError("Failed to download Kling video", data={"provider": "kling"}) from exc

    if not resp.ok:
        _raise_kling_http_error("video download", resp)
    return resp.content
