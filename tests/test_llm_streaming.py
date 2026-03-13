from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-llm-streaming.db")

from app.shared.services.llm_streaming import (
    _build_anthropic_payload,
    _extract_anthropic_http_error_message,
)


class AnthropicPayloadTests(unittest.TestCase):
    def test_build_payload_normalizes_system_messages_and_clamps_budget(self) -> None:
        payload = _build_anthropic_payload(
            system_prompt="Follow the brand voice.",
            messages=[
                {"role": "system", "content": "Internal instruction"},
                {"role": "user", "content": "Draft a landing page"},
            ],
            model="claude-sonnet-4-6",
            max_tokens=8192,
            thinking_budget=10000,
        )

        self.assertEqual(payload["messages"][0]["role"], "assistant")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["thinking"]["budget_tokens"], 8191)

    def test_extract_http_error_message_prefers_nested_anthropic_error(self) -> None:
        message = _extract_anthropic_http_error_message(
            b'{"type":"error","error":{"type":"invalid_request_error","message":"budget_tokens must be less than max_tokens"}}'
        )

        self.assertEqual(message, "budget_tokens must be less than max_tokens")
