from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app.modules.creative.serializers import serialize_asset


def make_asset(**overrides):
    defaults = {
        "id": uuid4(),
        "pack_id": uuid4(),
        "type": "video",
        "version": "1",
        "name": None,
        "template_id": None,
        "source_code": None,
        "output_key": "assets/pack/video.mp4",
        "preview_url": "https://provider.example.com/video.mp4",
        "preview_image_key": "assets/pack/video.jpg",
        "script": "Hook body CTA",
        "srt_key": "assets/pack/video.srt",
        "sprint_day": 4,
        "chat_messages": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class SerializeAssetTests(unittest.TestCase):
    @patch("app.modules.creative.serializers.get_asset_url")
    def test_serialize_asset_uses_storage_urls_for_saved_assets(self, mock_get_asset_url) -> None:
        mock_get_asset_url.side_effect = [
            "https://cdn.example.com/assets/pack/video.mp4",
            "https://cdn.example.com/assets/pack/video.jpg",
        ]

        asset = make_asset()

        serialized = serialize_asset(asset)

        self.assertEqual(serialized.output_url, "https://cdn.example.com/assets/pack/video.mp4")
        self.assertEqual(serialized.poster_url, "https://cdn.example.com/assets/pack/video.jpg")
        self.assertEqual(mock_get_asset_url.call_count, 2)

    @patch("app.modules.creative.serializers.get_asset_url")
    def test_serialize_asset_does_not_expose_provider_preview_url_as_output_url(
        self,
        mock_get_asset_url,
    ) -> None:
        asset = make_asset(output_key=None, preview_image_key=None)

        serialized = serialize_asset(asset)

        self.assertIsNone(serialized.output_url)
        self.assertIsNone(serialized.poster_url)
        mock_get_asset_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
