from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-builder-generation.db")

from app.modules.builder import generation as builder_generation
from app.modules.builder.generation import (
    _DEFAULT_APP_MARKER,
    create_website_generation_stream,
)
from app.shared.generation_schemas import GenerationMessage


class BuilderGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_mode_uses_builder_model(self) -> None:
        async def fake_create_text_stream(**kwargs):
            self.assertEqual(kwargs["max_tokens"], 8192)
            self.assertEqual(kwargs["model"], "builder-model")

            async def iterator():
                yield "ready"

            return iterator()

        with (
            patch.object(builder_generation, "get_builder_model", return_value="builder-model"),
            patch(
                "app.modules.builder.generation.create_text_stream",
                side_effect=fake_create_text_stream,
            ),
        ):
            stream = await create_website_generation_stream(
                messages=[GenerationMessage(role="user", content="Build the site now")],
                files={"/App.tsx": _DEFAULT_APP_MARKER},
                brand_context=None,
                selected_style=None,
            )

        chunks = [chunk async for chunk in stream]
        self.assertEqual(chunks, ["ready"])

    async def test_edit_mode_uses_reasoning_model(self) -> None:
        async def fake_create_text_stream(**kwargs):
            self.assertEqual(kwargs["max_tokens"], 8192)
            self.assertEqual(kwargs["model"], "reasoning-model")

            async def iterator():
                yield "patched"

            return iterator()

        with (
            patch.object(builder_generation, "get_reasoning_model", return_value="reasoning-model"),
            patch(
                "app.modules.builder.generation.create_text_stream",
                side_effect=fake_create_text_stream,
            ),
        ):
            stream = await create_website_generation_stream(
                messages=[GenerationMessage(role="user", content="Fix the spacing bug")],
                files={"/App.tsx": "export default function App() { return <main />; }"},
                brand_context=None,
                selected_style=None,
            )

        chunks = [chunk async for chunk in stream]
        self.assertEqual(chunks, ["patched"])
