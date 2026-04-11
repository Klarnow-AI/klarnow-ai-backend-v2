"""Unit tests for app.core.errors module."""

import pytest
from unittest.mock import MagicMock
from fastapi import status

from app.core.errors import (
    AppError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    BadRequestError,
    ConflictError,
    ServiceUnavailableError,
    BadGatewayError,
    GateBlockedError,
    DomainNotFoundError,
    DomainConflictError,
    DomainGateBlockedError,
    DomainServiceUnavailableError,
    ErrorInfo,
    resolve_error_info,
    build_error_payload,
    map_value_error_to_app_error,
    _default_error_info,
    _format_validation_errors,
    VALIDATION_ERROR_MESSAGE,
)


# ---------------------------------------------------------------------------
# ErrorInfo resolution
# ---------------------------------------------------------------------------

class TestDefaultErrorInfo:
    def test_401_returns_auth_unauthorized(self):
        info = _default_error_info(401)
        assert info.category == "auth"
        assert info.code == "unauthorized"
        assert info.retryable is False

    def test_403_returns_permission_forbidden(self):
        info = _default_error_info(403)
        assert info.category == "permission"
        assert info.code == "forbidden"
        assert info.retryable is False

    def test_404_returns_not_found(self):
        info = _default_error_info(404)
        assert info.category == "not_found"
        assert info.code == "not_found"
        assert info.retryable is False

    def test_409_returns_conflict(self):
        info = _default_error_info(409)
        assert info.category == "conflict"
        assert info.code == "conflict"
        assert info.retryable is False

    def test_422_returns_precondition_failed(self):
        info = _default_error_info(422)
        assert info.category == "conflict"
        assert info.code == "precondition_failed"
        assert info.retryable is False

    def test_429_returns_rate_limited(self):
        info = _default_error_info(429)
        assert info.category == "rate_limit"
        assert info.code == "rate_limited"
        assert info.retryable is True

    def test_502_returns_service_unavailable(self):
        info = _default_error_info(502)
        assert info.category == "service"
        assert info.code == "service_unavailable"
        assert info.retryable is True

    def test_503_returns_service_unavailable(self):
        info = _default_error_info(503)
        assert info.category == "service"
        assert info.code == "service_unavailable"
        assert info.retryable is True

    def test_504_returns_service_unavailable(self):
        info = _default_error_info(504)
        assert info.category == "service"
        assert info.code == "service_unavailable"
        assert info.retryable is True

    def test_500_returns_server_error(self):
        info = _default_error_info(500)
        assert info.category == "server"
        assert info.code == "server_error"
        assert info.retryable is True

    def test_400_returns_validation_bad_request(self):
        info = _default_error_info(400)
        assert info.category == "validation"
        assert info.code == "bad_request"
        assert info.retryable is False


class TestResolveErrorInfo:
    def test_uses_defaults_when_no_overrides(self):
        info = resolve_error_info(404)
        assert info.category == "not_found"
        assert info.code == "not_found"

    def test_overrides_category(self):
        info = resolve_error_info(404, category="custom_cat")
        assert info.category == "custom_cat"
        assert info.code == "not_found"

    def test_overrides_code(self):
        info = resolve_error_info(404, code="custom_code")
        assert info.code == "custom_code"

    def test_overrides_retryable(self):
        info = resolve_error_info(404, retryable=True)
        assert info.retryable is True

    def test_retryable_none_uses_default(self):
        info = resolve_error_info(500, retryable=None)
        assert info.retryable is True  # 500 default


# ---------------------------------------------------------------------------
# AppError and subclasses
# ---------------------------------------------------------------------------

class TestAppError:
    def test_default_status_code(self):
        err = AppError("test")
        assert err.status_code == 400
        assert err.message == "test"

    def test_custom_status_code(self):
        err = AppError("fail", status_code=503)
        assert err.status_code == 503
        assert err.retryable is True

    def test_data_defaults_to_empty_dict(self):
        err = AppError("test")
        assert err.data == {}

    def test_custom_data(self):
        err = AppError("test", data={"key": "val"})
        assert err.data == {"key": "val"}


class TestErrorSubclasses:
    def test_unauthorized_error(self):
        err = UnauthorizedError()
        assert err.status_code == 401
        assert err.message == "Unauthorized"
        assert err.category == "auth"
        assert err.retryable is False

    def test_unauthorized_custom_message(self):
        err = UnauthorizedError("Token expired")
        assert err.message == "Token expired"

    def test_forbidden_error(self):
        err = ForbiddenError()
        assert err.status_code == 403
        assert err.category == "permission"

    def test_not_found_error(self):
        err = NotFoundError()
        assert err.status_code == 404
        assert err.code == "not_found"

    def test_bad_request_error(self):
        err = BadRequestError()
        assert err.status_code == 400
        assert err.category == "validation"

    def test_conflict_error(self):
        err = ConflictError()
        assert err.status_code == 409

    def test_service_unavailable_error(self):
        err = ServiceUnavailableError()
        assert err.status_code == 503
        assert err.retryable is True

    def test_bad_gateway_error(self):
        err = BadGatewayError()
        assert err.status_code == 502
        assert err.code == "upstream_failure"

    def test_bad_gateway_with_data(self):
        err = BadGatewayError(data={"upstream": "openai"})
        assert err.data == {"upstream": "openai"}

    def test_gate_blocked_error(self):
        err = GateBlockedError("Build website first")
        assert err.status_code == 422
        assert err.code == "precondition_failed"


# ---------------------------------------------------------------------------
# Domain ValueError subclasses mapping
# ---------------------------------------------------------------------------

class TestMapValueErrorToAppError:
    def test_domain_not_found(self):
        exc = DomainNotFoundError("No such project")
        result = map_value_error_to_app_error(exc)
        assert isinstance(result, NotFoundError)
        assert result.message == "No such project"

    def test_domain_conflict(self):
        exc = DomainConflictError("Already exists")
        result = map_value_error_to_app_error(exc)
        assert isinstance(result, ConflictError)

    def test_domain_gate_blocked(self):
        exc = DomainGateBlockedError("Missing prerequisite")
        result = map_value_error_to_app_error(exc)
        assert isinstance(result, GateBlockedError)

    def test_domain_service_unavailable(self):
        exc = DomainServiceUnavailableError("Redis down")
        result = map_value_error_to_app_error(exc)
        assert isinstance(result, ServiceUnavailableError)

    def test_plain_value_error_becomes_bad_request(self):
        exc = ValueError("Something wrong")
        result = map_value_error_to_app_error(exc)
        assert isinstance(result, BadRequestError)

    def test_empty_value_error_gets_default_message(self):
        exc = ValueError("")
        result = map_value_error_to_app_error(exc)
        assert result.message == "Invalid request"


# ---------------------------------------------------------------------------
# build_error_payload
# ---------------------------------------------------------------------------

class TestBuildErrorPayload:
    def test_basic_payload_structure(self):
        payload = build_error_payload("Something failed", status_code=500)
        assert payload["isSuccess"] is False
        assert payload["message"] == "Something failed"
        assert payload["error"]["category"] == "server"
        assert payload["error"]["code"] == "server_error"
        assert payload["error"]["retryable"] is True
        assert isinstance(payload["data"], dict)

    def test_includes_request_id_from_request(self):
        mock_request = MagicMock()
        mock_request.state.request_id = "req-123"
        payload = build_error_payload("fail", request=mock_request)
        assert payload["data"]["request_id"] == "req-123"

    def test_includes_request_id_from_param(self):
        payload = build_error_payload("fail", request_id="req-456")
        assert payload["data"]["request_id"] == "req-456"

    def test_custom_data_preserved(self):
        payload = build_error_payload("fail", data={"detail": "extra"})
        assert payload["data"]["detail"] == "extra"

    def test_custom_category_and_code(self):
        payload = build_error_payload(
            "fail",
            status_code=400,
            category="custom",
            code="custom_code",
        )
        assert payload["error"]["category"] == "custom"
        assert payload["error"]["code"] == "custom_code"
