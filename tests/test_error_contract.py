from __future__ import annotations

import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-error-contract.db")

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import main as main_module
from app.core.errors import (
    AppError,
    NotFoundError,
    VALIDATION_ERROR_MESSAGE,
    app_error_handler,
    build_error_payload,
    http_exception_handler,
    request_validation_error_handler,
)


def _make_request(request_id: str = "req-123") -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }
    )
    request.state.request_id = request_id
    return request


def _decode(response) -> dict:
    return json.loads(response.body.decode("utf-8"))


class _FailureAlertValidationBody(BaseModel):
    email: str
    password: str


def _ensure_failure_alert_test_routes() -> None:
    existing_paths = {
        getattr(route, "path", "")
        for route in main_module.app.routes
    }

    if "/__test/failure-alert/not-found" not in existing_paths:
        @main_module.app.get("/__test/failure-alert/not-found")
        def failure_alert_not_found():
            raise NotFoundError("Pack not found")

    if "/__test/failure-alert/validation" not in existing_paths:
        @main_module.app.post("/__test/failure-alert/validation")
        def failure_alert_validation(body: _FailureAlertValidationBody):
            return {"email": body.email}

    if "/__test/failure-alert/redaction" not in existing_paths:
        @main_module.app.post("/__test/failure-alert/redaction")
        def failure_alert_redaction(body: dict):
            raise AppError("Bad request payload", status_code=400, data={"body": body})

    if "/__test/failure-alert/runtime-error" not in existing_paths:
        @main_module.app.get("/__test/failure-alert/runtime-error")
        def failure_alert_runtime_error():
            raise RuntimeError("database credentials exploded")

    if "/__test/failure-alert/success" not in existing_paths:
        @main_module.app.get("/__test/failure-alert/success")
        def failure_alert_success():
            return {"status": "ok"}


def _client() -> TestClient:
    _ensure_failure_alert_test_routes()
    return TestClient(main_module.app, raise_server_exceptions=False)


class ErrorContractTests(unittest.TestCase):
    def test_app_error_handler_returns_structured_not_found_payload(self) -> None:
        response = app_error_handler(_make_request(), NotFoundError("Pack not found"))
        payload = _decode(response)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["message"], "Pack not found")
        self.assertEqual(
            payload["error"],
            {
                "category": "not_found",
                "code": "not_found",
                "retryable": False,
            },
        )
        self.assertEqual(payload["data"]["request_id"], "req-123")

    def test_http_exception_handler_maps_rate_limit_category(self) -> None:
        response = http_exception_handler(
            _make_request(),
            StarletteHTTPException(status_code=429, detail="Slow down"),
        )
        payload = _decode(response)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(payload["message"], "Slow down")
        self.assertEqual(
            payload["error"],
            {
                "category": "rate_limit",
                "code": "rate_limited",
                "retryable": True,
            },
        )

    def test_request_validation_error_handler_uses_friendly_message_and_clean_fields(self) -> None:
        exc = RequestValidationError(
            [
                {
                    "loc": ("body", "email"),
                    "msg": "Field required",
                    "type": "missing",
                }
            ]
        )

        response = request_validation_error_handler(_make_request(), exc)
        payload = _decode(response)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["message"], VALIDATION_ERROR_MESSAGE)
        self.assertEqual(
            payload["error"],
            {
                "category": "validation",
                "code": "validation_error",
                "retryable": False,
            },
        )
        self.assertEqual(
            payload["data"]["errors"],
            [
                {
                    "field": "email",
                    "message": "Field required",
                    "type": "missing",
                }
            ],
        )

    def test_generic_exception_handler_hides_raw_message_in_production(self) -> None:
        request = _make_request("req-500")
        original_env = main_module.settings.app_env
        main_module.settings.app_env = "production"
        try:
            response = main_module._generic_exception_handler(
                request,
                RuntimeError("database credentials exploded"),
            )
        finally:
            main_module.settings.app_env = original_env

        payload = _decode(response)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload["message"], main_module.GENERIC_SERVER_ERROR_MESSAGE)
        self.assertEqual(
            payload["error"],
            {
                "category": "server",
                "code": "server_error",
                "retryable": True,
            },
        )
        self.assertEqual(payload["data"]["request_id"], "req-500")
        self.assertNotIn("database credentials exploded", payload["message"])

    def test_build_error_payload_matches_stream_error_shape(self) -> None:
        payload = build_error_payload(
            "Conversation not found",
            status_code=404,
            request_id="req-sse",
        )

        self.assertEqual(
            payload,
            {
                "isSuccess": False,
                "message": "Conversation not found",
                "error": {
                    "category": "not_found",
                    "code": "not_found",
                    "retryable": False,
                },
                "data": {"request_id": "req-sse"},
            },
        )


class FailureAlertTests(unittest.TestCase):
    @patch("app.core.failure_alerts.send_failure_alert_email")
    def test_not_found_response_queues_alert_with_status_location_trigger_and_solution(
        self,
        mock_send: Mock,
    ) -> None:
        with _client() as client:
            response = client.get("/__test/failure-alert/not-found")

        self.assertEqual(response.status_code, 404)
        mock_send.assert_called_once()
        alert = mock_send.call_args.args[0]
        self.assertEqual(alert.details["status_code"], 404)
        self.assertEqual(alert.details["location"]["path"], "/__test/failure-alert/not-found")
        self.assertEqual(alert.details["trigger"], "NotFoundError")
        self.assertIn("route and resource identifiers", alert.details["potential_solution"])
        self.assertEqual(alert.details["process"], "failure_alert_not_found")

    @patch("app.core.failure_alerts.send_failure_alert_email")
    def test_validation_error_alert_includes_field_errors_and_validation_solution(
        self,
        mock_send: Mock,
    ) -> None:
        with _client() as client:
            response = client.post(
                "/__test/failure-alert/validation",
                json={"password": "top-secret"},
            )

        self.assertEqual(response.status_code, 400)
        mock_send.assert_called_once()
        alert = mock_send.call_args.args[0]
        self.assertEqual(alert.details["error_details"]["message"], VALIDATION_ERROR_MESSAGE)
        self.assertEqual(
            alert.details["error_details"]["validation_errors"],
            [
                {
                    "field": "email",
                    "message": "Field required",
                    "type": "missing",
                }
            ],
        )
        self.assertEqual(alert.details["trigger"], "RequestValidationError")
        self.assertIn("Validate the request payload", alert.details["potential_solution"])

    @patch("app.core.failure_alerts.send_failure_alert_email")
    def test_production_500_hides_raw_message_in_response_but_includes_cause_in_alert(
        self,
        mock_send: Mock,
    ) -> None:
        original_env = main_module.settings.app_env
        main_module.settings.app_env = "production"
        try:
            with _client() as client:
                response = client.get("/__test/failure-alert/runtime-error")
        finally:
            main_module.settings.app_env = original_env

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["message"], main_module.GENERIC_SERVER_ERROR_MESSAGE)
        mock_send.assert_called_once()
        alert = mock_send.call_args.args[0]
        self.assertEqual(
            alert.details["error_details"]["message"],
            main_module.GENERIC_SERVER_ERROR_MESSAGE,
        )
        self.assertEqual(alert.details["cause"]["type"], "RuntimeError")
        self.assertIn("database credentials exploded", alert.details["cause"]["message"])
        self.assertIn("database credentials exploded", alert.details["traceback"])

    @patch("app.core.failure_alerts.send_failure_alert_email")
    def test_alert_redacts_sensitive_headers_body_and_query_values(
        self,
        mock_send: Mock,
    ) -> None:
        with _client() as client:
            response = client.post(
                "/__test/failure-alert/redaction?token=super-secret-token",
                headers={
                    "Authorization": "Bearer top-secret-token",
                    "Cookie": "sessionid=ultra-secret",
                    "X-Request-ID": "req-redact",
                },
                json={
                    "email": "user@example.com",
                    "password": "plain-text-password",
                    "nested": {"api_key": "provider-secret"},
                },
            )

        self.assertEqual(response.status_code, 400)
        mock_send.assert_called_once()
        alert = mock_send.call_args.args[0]
        self.assertEqual(alert.details["request_headers"]["authorization"], "[REDACTED]")
        self.assertEqual(alert.details["request_headers"]["cookie"], "[REDACTED]")
        self.assertEqual(alert.details["location"]["query_string"], "token=[REDACTED]")
        self.assertIn("[REDACTED]", alert.details["request_body_preview"])
        self.assertNotIn("plain-text-password", alert.details["request_body_preview"])
        self.assertNotIn("provider-secret", alert.details["request_body_preview"])

    @patch("app.core.failure_alerts.send_failure_alert_email")
    def test_success_response_does_not_queue_failure_alert(self, mock_send: Mock) -> None:
        with _client() as client:
            response = client.get("/__test/failure-alert/success")

        self.assertEqual(response.status_code, 200)
        mock_send.assert_not_called()

    @patch("app.core.failure_alerts.get_settings")
    def test_failure_alert_send_errors_do_not_change_api_response(
        self,
        mock_get_settings: Mock,
    ) -> None:
        fake_resend = SimpleNamespace(
            api_key="",
            Emails=SimpleNamespace(send=Mock(side_effect=RuntimeError("resend unavailable"))),
        )
        mock_get_settings.return_value = SimpleNamespace(
            failure_alert_to_email="alerts@example.com",
            support_email="support@example.com",
            resend_api_key="re_test",
            resend_from_email="noreply@example.com",
        )

        with patch.dict(sys.modules, {"resend": fake_resend}):
            with _client() as client:
                response = client.get("/__test/failure-alert/not-found")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "Pack not found")
        fake_resend.Emails.send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
