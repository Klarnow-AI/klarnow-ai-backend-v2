"""HTTP and domain exceptions and handlers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.failure_alerts import set_failure_alert_context


VALIDATION_ERROR_MESSAGE = "Some information needs attention. Please review and try again."


@dataclass(frozen=True)
class ErrorInfo:
    category: str
    code: str
    retryable: bool


def _default_error_info(status_code: int) -> ErrorInfo:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return ErrorInfo("auth", "unauthorized", False)
    if status_code == status.HTTP_403_FORBIDDEN:
        return ErrorInfo("permission", "forbidden", False)
    if status_code == status.HTTP_404_NOT_FOUND:
        return ErrorInfo("not_found", "not_found", False)
    if status_code == status.HTTP_409_CONFLICT:
        return ErrorInfo("conflict", "conflict", False)
    if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return ErrorInfo("conflict", "precondition_failed", False)
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return ErrorInfo("rate_limit", "rate_limited", True)
    if status_code in {
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_504_GATEWAY_TIMEOUT,
    }:
        return ErrorInfo("service", "service_unavailable", True)
    if status_code >= 500:
        return ErrorInfo("server", "server_error", True)
    return ErrorInfo("validation", "bad_request", False)


def resolve_error_info(
    status_code: int,
    *,
    category: str | None = None,
    code: str | None = None,
    retryable: bool | None = None,
) -> ErrorInfo:
    default = _default_error_info(status_code)
    return ErrorInfo(
        category=category or default.category,
        code=code or default.code,
        retryable=default.retryable if retryable is None else retryable,
    )


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: dict[str, Any] | None = None,
        *,
        category: str | None = None,
        code: str | None = None,
        retryable: bool | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.data = data or {}
        error_info = resolve_error_info(
            status_code,
            category=category,
            code=code,
            retryable=retryable,
        )
        self.category = error_info.category
        self.code = error_info.code
        self.retryable = error_info.retryable
        super().__init__(message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            category="auth",
            code="unauthorized",
            retryable=False,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message,
            status_code=status.HTTP_403_FORBIDDEN,
            category="permission",
            code="forbidden",
            retryable=False,
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(
            message,
            status_code=status.HTTP_404_NOT_FOUND,
            category="not_found",
            code="not_found",
            retryable=False,
        )


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            category="validation",
            code="bad_request",
            retryable=False,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(
            message,
            status_code=status.HTTP_409_CONFLICT,
            category="conflict",
            code="conflict",
            retryable=False,
        )


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            category="service",
            code="service_unavailable",
            retryable=True,
        )


class BadGatewayError(AppError):
    def __init__(
        self,
        message: str = "Bad gateway",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            data=data,
            category="service",
            code="upstream_failure",
            retryable=True,
        )


class GateBlockedError(AppError):
    """Raised when a stage gate blocks progression (e.g. build website before Brand OS)."""

    def __init__(self, message: str):
        super().__init__(
            message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            category="conflict",
            code="precondition_failed",
            retryable=False,
        )


# ---------------------------------------------------------------------------
# Typed ValueError subclasses — raise these instead of plain ValueError so
# map_value_error_to_app_error can use isinstance checks rather than fragile
# string matching.
# ---------------------------------------------------------------------------


class DomainNotFoundError(ValueError):
    """Resource not found or access denied — maps to 404."""


class DomainConflictError(ValueError):
    """State conflict (duplicate, locked, already active) — maps to 409."""


class DomainGateBlockedError(ValueError):
    """Prerequisite not met — maps to 422."""


class DomainServiceUnavailableError(ValueError):
    """External service or integration not configured — maps to 503."""


def _request_data(request: Request) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", None)
    return {"request_id": request_id} if request_id else {}


def build_error_payload(
    message: str,
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    request: Request | None = None,
    request_id: str | None = None,
    data: dict[str, Any] | None = None,
    category: str | None = None,
    code: str | None = None,
    retryable: bool | None = None,
) -> dict[str, Any]:
    error_info = resolve_error_info(
        status_code,
        category=category,
        code=code,
        retryable=retryable,
    )
    payload_data = dict(data or {})
    if request is not None:
        payload_data.update(
            {k: v for k, v in _request_data(request).items() if k not in payload_data}
        )
    elif request_id and "request_id" not in payload_data:
        payload_data["request_id"] = request_id
    return {
        "isSuccess": False,
        "message": message,
        "error": {
            "category": error_info.category,
            "code": error_info.code,
            "retryable": error_info.retryable,
        },
        "data": payload_data,
    }


def error_response(
    request: Request,
    message: str,
    data: dict[str, Any] | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    *,
    category: str | None = None,
    code: str | None = None,
    retryable: bool | None = None,
    cause_exc: Exception | None = None,
    traceback_text: str | None = None,
) -> JSONResponse:
    payload = build_error_payload(
        message,
        status_code=status_code,
        request=request,
        data=data,
        category=category,
        code=code,
        retryable=retryable,
    )
    error_meta = payload.get("error", {})
    set_failure_alert_context(
        request,
        status_code=status_code,
        message=message,
        data=data,
        category=str(error_meta.get("category") or "").strip() or None,
        code=str(error_meta.get("code") or "").strip() or None,
        retryable=error_meta.get("retryable")
        if isinstance(error_meta.get("retryable"), bool)
        else None,
        response_payload=payload,
        cause_exc=cause_exc,
        traceback_text=traceback_text,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    return error_response(
        request,
        message=exc.message,
        data=exc.data,
        status_code=exc.status_code,
        category=exc.category,
        code=exc.code,
        retryable=exc.retryable,
        cause_exc=exc,
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail or HTTPStatus(exc.status_code).phrase
    category: str | None = None
    code: str | None = None
    retryable: bool | None = None

    if isinstance(detail, Mapping):
        message = str(detail.get("message") or HTTPStatus(exc.status_code).phrase)
        raw_data = detail.get("data", {})
        raw_error = detail.get("error")
        if isinstance(raw_data, Mapping):
            data = dict(raw_data)
        elif raw_data is None:
            data = {}
        else:
            data = {"detail": raw_data}
        if isinstance(raw_error, Mapping):
            raw_category = raw_error.get("category")
            raw_code = raw_error.get("code")
            raw_retryable = raw_error.get("retryable")
            category = str(raw_category).strip() if raw_category else None
            code = str(raw_code).strip() if raw_code else None
            retryable = raw_retryable if isinstance(raw_retryable, bool) else None
    else:
        message = str(detail)
        data = {}

    return error_response(
        request,
        message=message,
        data=data,
        status_code=exc.status_code,
        category=category,
        code=code,
        retryable=retryable,
        cause_exc=exc,
    )


def _format_validation_errors(exc: RequestValidationError) -> tuple[str, list[dict[str, str]]]:
    formatted: list[dict[str, str]] = []
    for error in exc.errors():
        raw_location = [str(part) for part in error.get("loc", [])]
        while raw_location and raw_location[0] in {"body", "query", "path"}:
            raw_location.pop(0)
        location = ".".join(raw_location) or "request"
        message = str(error.get("msg", "Invalid value"))
        error_type = str(error.get("type", "validation_error"))
        formatted.append(
            {
                "field": location,
                "message": message,
                "type": error_type,
            }
        )

    if not formatted:
        return VALIDATION_ERROR_MESSAGE, formatted

    return VALIDATION_ERROR_MESSAGE, formatted


def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    detail, errors = _format_validation_errors(exc)
    return error_response(
        request,
        message=detail,
        data={"errors": errors},
        status_code=status.HTTP_400_BAD_REQUEST,
        category="validation",
        code="validation_error",
        retryable=False,
        cause_exc=exc,
    )


def map_value_error_to_app_error(exc: ValueError) -> AppError:
    message = str(exc).strip() or "Invalid request"
    if isinstance(exc, DomainNotFoundError):
        return NotFoundError(message)
    if isinstance(exc, DomainConflictError):
        return ConflictError(message)
    if isinstance(exc, DomainGateBlockedError):
        return GateBlockedError(message)
    if isinstance(exc, DomainServiceUnavailableError):
        return ServiceUnavailableError(message)
    return BadRequestError(message)


def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    mapped = map_value_error_to_app_error(exc)
    return error_response(
        request,
        message=mapped.message,
        data=mapped.data,
        status_code=mapped.status_code,
        category=mapped.category,
        code=mapped.code,
        retryable=mapped.retryable,
        cause_exc=exc,
    )
