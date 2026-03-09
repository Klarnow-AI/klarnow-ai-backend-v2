"""HTTP and domain exceptions and handlers."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.data = data or {}
        super().__init__(message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class BadGatewayError(AppError):
    def __init__(
        self,
        message: str = "Bad gateway",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, data=data)


class GateBlockedError(AppError):
    """Raised when a stage gate blocks progression (e.g. build website before Brand OS)."""

    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


def _request_data(request: Request) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", None)
    return {"request_id": request_id} if request_id else {}


def error_response(
    request: Request,
    message: str,
    data: dict[str, Any] | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    payload_data = dict(data or {})
    payload_data.update({k: v for k, v in _request_data(request).items() if k not in payload_data})
    return JSONResponse(
        status_code=status_code,
        content={
            "isSuccess": False,
            "message": message,
            "data": payload_data,
        },
    )


def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    return error_response(
        request,
        message=exc.message,
        data=exc.data,
        status_code=exc.status_code,
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail or HTTPStatus(exc.status_code).phrase

    if isinstance(detail, Mapping):
        message = str(detail.get("message") or HTTPStatus(exc.status_code).phrase)
        raw_data = detail.get("data", {})
        if isinstance(raw_data, Mapping):
            data = dict(raw_data)
        elif raw_data is None:
            data = {}
        else:
            data = {"detail": raw_data}
    else:
        message = str(detail)
        data = {}

    return error_response(
        request,
        message=message,
        data=data,
        status_code=exc.status_code,
    )


def _format_validation_errors(exc: RequestValidationError) -> tuple[str, list[dict[str, str]]]:
    formatted: list[dict[str, str]] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", [])) or "request"
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
        return "Invalid request payload.", formatted

    summary = "; ".join(f"{item['field']}: {item['message']}" for item in formatted[:3])
    if len(formatted) > 3:
        summary += f" (+{len(formatted) - 3} more)"
    return f"Invalid request payload. {summary}", formatted


def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    detail, errors = _format_validation_errors(exc)
    return error_response(
        request,
        message=f"Validation error: {detail}",
        data={"errors": errors},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


_SERVICE_UNAVAILABLE_MARKERS = (
    "must be configured",
    "not configured",
)

_CONFLICT_MARKERS = (
    "already has an active",
    "already active",
    "already completed",
    "cannot update locked",
    "cannot be rendered; status=",
)

_NOT_FOUND_MARKERS = (
    "not found",
    "access denied",
    "no active sprint",
    "no day card",
    "no response rules found",
)

_PRECONDITION_MARKERS = (
    "before generating",
    "before starting",
    "before creating",
    "before proceeding",
    "before rendering",
)


def map_value_error_to_app_error(exc: ValueError) -> AppError:
    message = str(exc).strip() or "Invalid request"
    lower = message.lower()

    if any(marker in lower for marker in _SERVICE_UNAVAILABLE_MARKERS):
        return ServiceUnavailableError(message)
    if any(marker in lower for marker in _CONFLICT_MARKERS):
        return ConflictError(message)
    if any(marker in lower for marker in _NOT_FOUND_MARKERS):
        return NotFoundError(message)
    if any(marker in lower for marker in _PRECONDITION_MARKERS):
        return GateBlockedError(message)
    return BadRequestError(message)


def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return app_error_handler(request, map_value_error_to_app_error(exc))
