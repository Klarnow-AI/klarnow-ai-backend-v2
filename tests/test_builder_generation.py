from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-builder-generation.db")

from app.modules.builder.generation import (
    _DEFAULT_APP_MARKER,
    create_website_generation_stream,
)
from app.shared.generation_schemas import GenerationMessage


class BuilderGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_mode_reserves_room_for_output_when_setting_thinking_budget(self) -> None:
        async def fake_create_text_stream_with_fallback(**kwargs):
            self.assertEqual(kwargs["max_tokens"], 8192)
            self.assertEqual(kwargs["anthropic_thinking_budget"], 6144)

            async def iterator():
                yield "ready"

            return iterator()

        with patch(
            "app.modules.builder.generation.create_text_stream_with_fallback",
            side_effect=fake_create_text_stream_with_fallback,
        ):
            stream = await create_website_generation_stream(
                messages=[GenerationMessage(role="user", content="Build the site now")],
                files={"/App.tsx": _DEFAULT_APP_MARKER},
                brand_context=None,
                selected_style=None,
            )

        chunks = [chunk async for chunk in stream]
        self.assertEqual(chunks, ["ready"])

    async def test_edit_mode_keeps_existing_thinking_budget_when_it_already_fits(self) -> None:
        async def fake_create_text_stream_with_fallback(**kwargs):
            self.assertEqual(kwargs["max_tokens"], 8192)
            self.assertEqual(kwargs["anthropic_thinking_budget"], 6000)

            async def iterator():
                yield "patched"

            return iterator()

        with patch(
            "app.modules.builder.generation.create_text_stream_with_fallback",
            side_effect=fake_create_text_stream_with_fallback,
        ):
            stream = await create_website_generation_stream(
                messages=[GenerationMessage(role="user", content="Fix the spacing bug")],
                files={"/App.tsx": "export default function App() { return <main />; }"},
                brand_context=None,
                selected_style=None,
            )

        chunks = [chunk async for chunk in stream]
        self.assertEqual(chunks, ["patched"])
