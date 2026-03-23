"""Failure alert email generation and delivery for unsuccessful API requests."""

from __future__ import annotations

import asyncio
import html
import json
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request, Response
from starlette.background import BackgroundTask, BackgroundTasks

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("klarnow.failure_alerts")

MAX_BODY_CAPTURE_BYTES = 64 * 1024
MAX_PREVIEW_CHARS = 4_000
PREVIEWABLE_CONTENT_TYPES = (
    "application/json",
    "application/problem+json",
    "application/x-www-form-urlencoded",
    "text/plain",
    "text/",
)
SAFE_HEADER_NAMES = ("origin", "user-agent", "x-request-id", "content-type")
SENSITIVE_HEADER_NAMES = ("authorization", "cookie")
SENSITIVE_KEY_MARKERS = (
    "authorization",
    "cookie",
    "password",
    "token",
    "secret",
    "apikey",
    "accesskey",
    "sessionid",
)
FREEFORM_SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(password|token|secret|api[_-]?key|authorization|cookie)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^&,\s]+)"
)
FAILURE_ALERT_RATE_LIMIT_WINDOW_SECONDS = 1.0
FAILURE_ALERT_MAX_SENDS_PER_WINDOW = 4
FAILURE_ALERT_MAX_RETRY_ATTEMPTS = 3
FAILURE_ALERT_DEFAULT_RETRY_AFTER_SECONDS = 1.0
FAILURE_ALERT_MAX_RETRY_AFTER_SECONDS = 30.0

_FAILURE_ALERT_RATE_LIMIT_LOCK = asyncio.Lock()
_FAILURE_ALERT_SCHEDULED_SEND_TIMES: deque[float] = deque(
    maxlen=FAILURE_ALERT_MAX_SENDS_PER_WINDOW
)
_FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL = 0.0


@dataclass(frozen=True)
class FailureAlert:
    subject: str
    text: str
    html: str
    details: dict[str, Any]


def set_failure_alert_context(
    request: Request,
    *,
    status_code: int,
    message: str,
    data: dict[str, Any] | None = None,
    category: str | None = None,
    code: str | None = None,
    retryable: bool | None = None,
    response_payload: dict[str, Any] | None = None,
    cause_exc: Exception | None = None,
    traceback_text: str | None = None,
) -> None:
    request.state.failure_alert_context = {
        "status_code": status_code,
        "message": message,
        "data": dict(data or {}),
        "category": category,
        "code": code,
        "retryable": retryable,
        "response_payload": response_payload,
        "cause_type": cause_exc.__class__.__name__ if cause_exc is not None else None,
        "cause_message": str(cause_exc).strip() if cause_exc is not None else None,
        "traceback": traceback_text,
    }


async def capture_request_body_preview(request: Request) -> None:
    if hasattr(request.state, "failure_alert_request_body_preview"):
        return

    content_type = _normalize_content_type(request.headers.get("content-type"))
    if not _is_previewable_content_type(content_type):
        request.state.failure_alert_request_body_preview = None
        return

    try:
        content_length = int(request.headers.get("content-length", "0") or "0")
    except ValueError:
        content_length = 0

    if content_length > MAX_BODY_CAPTURE_BYTES:
        request.state.failure_alert_request_body_preview = (
            f"<request body omitted: content-length {content_length} exceeds {MAX_BODY_CAPTURE_BYTES} bytes>"
        )
        return

    try:
        body = await request.body()
    except Exception as exc:  # pragma: no cover - defensive fallback
        request.state.failure_alert_request_body_preview = (
            f"<request body unavailable: {exc.__class__.__name__}>"
        )
        return

    preview, _ = _build_body_preview(body, content_type)
    request.state.failure_alert_request_body_preview = preview


def queue_failure_alert_if_needed(request: Request, response: Response) -> None:
    if response.status_code < 400:
        return
    if getattr(request.state, "failure_alert_queued", False):
        return

    try:
        alert = build_failure_alert(request, response)
    except Exception:  # pragma: no cover - defensive fallback
        logger.exception(
            "Failed to build failure alert request_id=%s status_code=%s",
            getattr(request.state, "request_id", "-"),
            response.status_code,
        )
        return

    request.state.failure_alert_queued = True
    _append_background_task(response, send_failure_alert_email, alert)


def build_failure_alert(request: Request, response: Response) -> FailureAlert | None:
    status_code = response.status_code
    if status_code < 400:
        return None

    context = _get_failure_alert_context(request)
    response_preview, response_data = _get_response_preview_and_data(response, context)
    error_details = _build_error_details(status_code, context, response_data)
    cause = _build_cause(status_code, context, response_data)
    details = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": status_code,
        "error_details": error_details,
        "location": {
            "method": request.method,
            "path": request.url.path,
            "query_string": _build_query_string_preview(request),
            "client_host": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
        "cause": cause,
        "process": _resolve_process_name(request),
        "trigger": _build_trigger(status_code, context, error_details),
        "potential_solution": _potential_solution(status_code),
        "request_headers": _collect_request_headers(request),
        "request_body_preview": getattr(request.state, "failure_alert_request_body_preview", None),
        "response_body_preview": response_preview,
        "traceback": context.get("traceback") if context else None,
    }

    method = request.method.upper()
    path = request.url.path
    subject = f"[Klarnow Failure Alert] {status_code} {method} {path}"
    text = _render_text(details)
    html_body = f"<html><body><pre>{html.escape(text)}</pre></body></html>"
    return FailureAlert(subject=subject, text=text, html=html_body, details=details)


async def send_failure_alert_email(alert: FailureAlert) -> bool:
    settings = get_settings()
    to_email = (
        getattr(settings, "failure_alert_to_email", "") or getattr(settings, "support_email", "")
    ).strip()
    request_id = str(alert.details.get("location", {}).get("request_id") or "-")
    status_code = alert.details.get("status_code")
    if not to_email or not settings.resend_api_key:
        logger.info(
            "Failure alert email disabled request_id=%s status_code=%s recipient=%s resend=%s",
            request_id,
            status_code,
            bool(to_email),
            bool(settings.resend_api_key),
        )
        return False

    try:
        import resend
    except Exception as exc:
        logger.warning(
            "Failure alert email send failed request_id=%s status_code=%s error=%s",
            request_id,
            status_code,
            exc,
        )
        return False

    resend.api_key = settings.resend_api_key
    payload = {
        "from": settings.resend_from_email or "onboarding@resend.dev",
        "to": to_email,
        "subject": alert.subject,
        "text": alert.text,
        "html": alert.html,
    }

    for attempt in range(1, FAILURE_ALERT_MAX_RETRY_ATTEMPTS + 1):
        await _wait_for_failure_alert_send_slot()
        try:
            resend.Emails.send(payload)
            return True
        except Exception as exc:
            if _is_failure_alert_rate_limit_error(exc) and attempt < FAILURE_ALERT_MAX_RETRY_ATTEMPTS:
                retry_after_seconds = _resolve_failure_alert_retry_after_seconds(exc)
                await _set_failure_alert_provider_cooldown(retry_after_seconds)
                logger.warning(
                    "Failure alert email rate limited request_id=%s status_code=%s attempt=%s retry_in_seconds=%.2f error=%s",
                    request_id,
                    status_code,
                    attempt,
                    retry_after_seconds,
                    exc,
                )
                continue
            logger.warning(
                "Failure alert email send failed request_id=%s status_code=%s attempt=%s error=%s",
                request_id,
                status_code,
                attempt,
                exc,
            )
            return False
    return False


async def _wait_for_failure_alert_send_slot() -> None:
    delay_seconds = await _reserve_failure_alert_send_delay()
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)


async def _reserve_failure_alert_send_delay() -> float:
    now = time.monotonic()
    async with _FAILURE_ALERT_RATE_LIMIT_LOCK:
        scheduled_at = max(now, _FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL)
        if len(_FAILURE_ALERT_SCHEDULED_SEND_TIMES) >= FAILURE_ALERT_MAX_SENDS_PER_WINDOW:
            scheduled_at = max(
                scheduled_at,
                _FAILURE_ALERT_SCHEDULED_SEND_TIMES[0] + FAILURE_ALERT_RATE_LIMIT_WINDOW_SECONDS,
            )
        _FAILURE_ALERT_SCHEDULED_SEND_TIMES.append(scheduled_at)
    return max(0.0, scheduled_at - now)


async def _set_failure_alert_provider_cooldown(retry_after_seconds: float) -> None:
    bounded_retry_after_seconds = max(
        FAILURE_ALERT_DEFAULT_RETRY_AFTER_SECONDS,
        min(retry_after_seconds, FAILURE_ALERT_MAX_RETRY_AFTER_SECONDS),
    )
    async with _FAILURE_ALERT_RATE_LIMIT_LOCK:
        global _FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL
        _FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL = max(
            _FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL,
            time.monotonic() + bounded_retry_after_seconds,
        )


def _is_failure_alert_rate_limit_error(exc: Exception) -> bool:
    provider_status_code = _extract_failure_alert_provider_status_code(exc)
    if provider_status_code == 429:
        return True
    message = str(exc).lower()
    return "too many requests" in message or "rate limit" in message


def _resolve_failure_alert_retry_after_seconds(exc: Exception) -> float:
    candidates = [
        getattr(exc, "retry_after", None),
        getattr(exc, "retry_after_seconds", None),
    ]
    for header_name in ("retry-after", "ratelimit-reset", "x-ratelimit-reset"):
        header_value = _extract_failure_alert_exception_header(exc, header_name)
        if header_value is not None:
            candidates.append(header_value)

    for candidate in candidates:
        retry_after_seconds = _parse_failure_alert_retry_after_seconds(candidate)
        if retry_after_seconds is not None:
            return retry_after_seconds
    return FAILURE_ALERT_DEFAULT_RETRY_AFTER_SECONDS


def _extract_failure_alert_provider_status_code(exc: Exception) -> int | None:
    candidates = [
        getattr(exc, "status_code", None),
        getattr(exc, "http_status", None),
    ]
    response = getattr(exc, "response", None)
    if response is not None:
        candidates.append(getattr(response, "status_code", None))

    for candidate in candidates:
        try:
            if candidate is not None:
                return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _extract_failure_alert_exception_header(exc: Exception, header_name: str) -> Any | None:
    header_sources = [
        getattr(exc, "headers", None),
        getattr(getattr(exc, "response", None), "headers", None),
    ]
    for header_source in header_sources:
        if header_source is None or not hasattr(header_source, "get"):
            continue
        header_value = header_source.get(header_name)
        if header_value is None:
            header_value = header_source.get(header_name.title())
        if header_value is not None:
            return header_value
    return None


def _parse_failure_alert_retry_after_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return max(0.0, float(value))

    text = str(value).strip()
    if not text:
        return None

    try:
        return max(0.0, float(text))
    except ValueError:
        pass

    try:
        retry_after_at = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None

    if retry_after_at.tzinfo is None:
        retry_after_at = retry_after_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_after_at - datetime.now(timezone.utc)).total_seconds())


async def _reset_failure_alert_rate_limit_state() -> None:
    async with _FAILURE_ALERT_RATE_LIMIT_LOCK:
        _FAILURE_ALERT_SCHEDULED_SEND_TIMES.clear()
        global _FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL
        _FAILURE_ALERT_PROVIDER_COOLDOWN_UNTIL = 0.0


def _append_background_task(response: Response, func, *args) -> None:
    background = response.background
    if background is None:
        response.background = BackgroundTask(func, *args)
        return
    if isinstance(background, BackgroundTasks):
        background.add_task(func, *args)
        return

    tasks = BackgroundTasks()
    if isinstance(background, BackgroundTask):
        tasks.add_task(background.func, *background.args, **background.kwargs)
    else:  # pragma: no cover - Starlette uses BackgroundTask/BackgroundTasks
        tasks.add_task(background)
    tasks.add_task(func, *args)
    response.background = tasks


def _get_failure_alert_context(request: Request) -> dict[str, Any] | None:
    context = getattr(request.state, "failure_alert_context", None)
    return context if isinstance(context, dict) else None


def _build_error_details(
    status_code: int,
    context: dict[str, Any] | None,
    response_data: Any,
) -> dict[str, Any]:
    message = None
    category = None
    code = None
    retryable = None
    validation_errors: list[dict[str, Any]] = []

    if context:
        message = _clean_text(context.get("message"))
        category = _clean_text(context.get("category"))
        code = _clean_text(context.get("code"))
        retryable = context.get("retryable") if isinstance(context.get("retryable"), bool) else None
        data = context.get("data")
        if isinstance(data, dict) and isinstance(data.get("errors"), list):
            validation_errors = [
                item for item in data["errors"] if isinstance(item, dict)
            ]

    if isinstance(response_data, dict):
        message = message or _clean_text(response_data.get("message")) or _clean_text(
            response_data.get("detail")
        )
        raw_error = response_data.get("error")
        if isinstance(raw_error, dict):
            category = category or _clean_text(raw_error.get("category"))
            code = code or _clean_text(raw_error.get("code"))
            if retryable is None and isinstance(raw_error.get("retryable"), bool):
                retryable = raw_error.get("retryable")
        raw_data = response_data.get("data")
        if isinstance(raw_data, dict) and not validation_errors and isinstance(raw_data.get("errors"), list):
            validation_errors = [
                item for item in raw_data["errors"] if isinstance(item, dict)
            ]
    elif isinstance(response_data, str):
        message = message or _clean_text(response_data)

    return {
        "message": message or HTTPStatus(status_code).phrase,
        "category": category,
        "code": code,
        "retryable": retryable,
        "validation_errors": validation_errors,
    }


def _build_cause(
    status_code: int,
    context: dict[str, Any] | None,
    response_data: Any,
) -> dict[str, Any]:
    cause_type = _clean_text(context.get("cause_type")) if context else None
    cause_message = _clean_text(context.get("cause_message")) if context else None
    if cause_message:
        return {"type": cause_type, "message": cause_message}
    if isinstance(response_data, dict):
        message = _clean_text(response_data.get("message")) or _clean_text(response_data.get("detail"))
        if message:
            return {"type": cause_type, "message": message}
    if isinstance(response_data, str) and _clean_text(response_data):
        return {"type": cause_type, "message": _clean_text(response_data)}
    return {"type": cause_type, "message": HTTPStatus(status_code).phrase}


def _build_trigger(
    status_code: int,
    context: dict[str, Any] | None,
    error_details: dict[str, Any],
) -> str:
    if context and _clean_text(context.get("cause_type")):
        return _clean_text(context["cause_type"]) or f"http_status_{status_code}"
    category = _clean_text(error_details.get("category"))
    code = _clean_text(error_details.get("code"))
    if category and code:
        return f"{category}:{code}"
    if category:
        return category
    if code:
        return code
    return f"http_status_{status_code}"


def _resolve_process_name(request: Request) -> str:
    endpoint = request.scope.get("endpoint")
    if endpoint is not None:
        name = getattr(endpoint, "__name__", None) or getattr(endpoint, "__qualname__", None)
        if isinstance(name, str) and name.strip():
            return name.strip()
    route = request.scope.get("route")
    route_name = getattr(route, "name", None)
    if isinstance(route_name, str) and route_name.strip():
        return route_name.strip()
    return f"{request.method.upper()} {request.url.path}"


def _collect_request_headers(request: Request) -> dict[str, str]:
    selected: dict[str, str] = {}
    for header_name in SAFE_HEADER_NAMES:
        value = request.headers.get(header_name)
        if value:
            selected[header_name] = _truncate_text(value, 500)
    for header_name in SENSITIVE_HEADER_NAMES:
        if request.headers.get(header_name):
            selected[header_name] = "[REDACTED]"
    return selected


def _build_query_string_preview(request: Request) -> str:
    pairs: list[str] = []
    for key, value in request.query_params.multi_items():
        sanitized_value = "[REDACTED]" if _is_sensitive_key(key) else value
        pairs.append(f"{key}={sanitized_value}")
    return "&".join(pairs)


def _get_response_preview_and_data(
    response: Response,
    context: dict[str, Any] | None,
) -> tuple[str | None, Any]:
    if context and isinstance(context.get("response_payload"), dict):
        payload = _sanitize_value(context["response_payload"])
        return _truncate_text(_to_pretty_json(payload), MAX_PREVIEW_CHARS), payload

    body = getattr(response, "body", None)
    if not isinstance(body, (bytes, bytearray)):
        return None, None
    content_type = _normalize_content_type(response.headers.get("content-type") or getattr(response, "media_type", None))
    return _build_body_preview(bytes(body), content_type)


def _build_body_preview(body: bytes, content_type: str | None) -> tuple[str | None, Any]:
    if not body:
        return None, None

    content_type = _normalize_content_type(content_type)
    text = body.decode("utf-8", errors="replace")
    if content_type and (content_type == "application/json" or content_type.endswith("+json")):
        try:
            payload = _sanitize_value(json.loads(text))
            return _truncate_text(_to_pretty_json(payload), MAX_PREVIEW_CHARS), payload
        except json.JSONDecodeError:
            sanitized_text = _sanitize_freeform_text(text)
            return _truncate_text(sanitized_text, MAX_PREVIEW_CHARS), _truncate_text(
                sanitized_text, MAX_PREVIEW_CHARS
            )

    if content_type == "application/x-www-form-urlencoded":
        parsed = parse_qs(text, keep_blank_values=True)
        flattened: dict[str, Any] = {}
        for key, values in parsed.items():
            flattened[key] = values[0] if len(values) == 1 else values
        payload = _sanitize_value(flattened)
        return _truncate_text(_to_pretty_json(payload), MAX_PREVIEW_CHARS), payload

    if _is_previewable_content_type(content_type):
        sanitized_text = _sanitize_freeform_text(text)
        return _truncate_text(sanitized_text, MAX_PREVIEW_CHARS), _truncate_text(
            sanitized_text, MAX_PREVIEW_CHARS
        )

    return None, None


def _sanitize_value(value: Any, key: str | None = None) -> Any:
    if key and _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _sanitize_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        return _truncate_text(value, MAX_PREVIEW_CHARS)
    return value


def _is_sensitive_key(value: str | None) -> bool:
    if not value:
        return False
    normalized = "".join(ch for ch in value.lower() if ch.isalnum())
    return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)


def _potential_solution(status_code: int) -> str:
    if status_code in {400, 422}:
        return "Validate the request payload and required fields before retrying."
    if status_code == 401:
        return "Check authentication, refresh flow, and session expiry before retrying."
    if status_code == 403:
        return "Verify the caller has the required permissions or resource ownership."
    if status_code == 404:
        return "Verify the route and resource identifiers exist and match the requested tenant/state."
    if status_code == 409:
        return "Inspect current resource state for duplicates or conflicting updates."
    if status_code == 429:
        return "Throttle the caller and inspect rate-limit thresholds or bursts."
    if status_code in {502, 503, 504}:
        return "Inspect upstream dependency health, timeouts, and retryability."
    if status_code >= 500:
        return "Inspect the traceback, request ID, and recent deploy or configuration changes."
    return "Inspect the request and resource state to understand why the API rejected it."


def _sanitize_freeform_text(text: str) -> str:
    return FREEFORM_SENSITIVE_PATTERN.sub(r"\1\2[REDACTED]", text)


def _render_text(details: dict[str, Any]) -> str:
    lines = [
        "Klarnow API failure alert",
        f"Timestamp: {details['timestamp']}",
        f"Status code: {details['status_code']}",
        f"Process: {details['process']}",
        f"Trigger: {details['trigger']}",
        f"Potential solution: {details['potential_solution']}",
        "",
        "Error details:",
        _to_pretty_json(details["error_details"]),
        "",
        "Location:",
        _to_pretty_json(details["location"]),
        "",
        "Cause:",
        _to_pretty_json(details["cause"]),
        "",
        "Request headers:",
        _to_pretty_json(details["request_headers"]),
        "",
        "Request body preview:",
        details["request_body_preview"] or "<none>",
        "",
        "Response body preview:",
        details["response_body_preview"] or "<none>",
    ]
    traceback_text = details.get("traceback")
    if traceback_text:
        lines.extend(["", "Traceback:", traceback_text])
    return "\n".join(lines)


def _normalize_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def _is_previewable_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    return any(
        content_type == known or content_type.startswith(known)
        for known in PREVIEWABLE_CONTENT_TYPES
    )


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truncate_text(value: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "...<truncated>"


def _to_pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str, sort_keys=True)
