from __future__ import annotations

import unittest

from app.shared.services.openai_compatible import (
    get_image_generation_extra_body_attempts,
    is_unsupported_output_modalities_error,
)


class ImageGenerationModalitiesTests(unittest.TestCase):
    def test_prefers_text_and_image_modalities_for_gemini_models(self) -> None:
        attempts = get_image_generation_extra_body_attempts(
            "google/gemini-3.1-flash-image-preview",
            aspect_ratio="16:9",
            image_size="4K",
        )

        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["modalities"], ["image", "text"])
        self.assertEqual(attempts[1]["modalities"], ["image"])
        self.assertEqual(attempts[0]["image_config"]["aspect_ratio"], "16:9")
        self.assertEqual(attempts[0]["image_config"]["image_size"], "4K")

    def test_prefers_image_only_modalities_for_sourceful_models(self) -> None:
        attempts = get_image_generation_extra_body_attempts(
            "sourceful/riverflow-v2-pro",
            aspect_ratio="1:1",
            image_size="1K",
        )

        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["modalities"], ["image"])
        self.assertEqual(attempts[1]["modalities"], ["image", "text"])

    def test_prefers_image_only_modalities_for_flux_models(self) -> None:
        attempts = get_image_generation_extra_body_attempts(
            "black-forest-labs/flux-1.1-pro",
            aspect_ratio="1:1",
            image_size="1K",
        )

        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["modalities"], ["image"])
        self.assertEqual(attempts[1]["modalities"], ["image", "text"])

    def test_detects_unsupported_output_modalities_errors(self) -> None:
        exc = Exception(
            "{'error': {'message': 'No endpoints found that support the requested output modalities: image, text', 'code': 404}}"
        )

        self.assertTrue(is_unsupported_output_modalities_error(exc))
        self.assertFalse(is_unsupported_output_modalities_error(Exception("Different failure")))
