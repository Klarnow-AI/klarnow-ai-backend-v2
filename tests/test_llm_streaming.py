from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-llm-streaming.db")

from app.shared.services.llm_streaming import create_text_stream


class StreamingConfigTests(unittest.TestCase):
    def test_requires_openrouter_provider(self) -> None:
        with patch("app.shared.services.llm_streaming.create_async_openai_client", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "OPENROUTER_API_KEY"):
                asyncio.run(
                    create_text_stream(
                        system_prompt="You are helpful.",
                        messages=[{"role": "user", "content": "Hello"}],
                    )
                )


if __name__ == "__main__":
    unittest.main()
