from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core import storage


class GetAssetUrlTests(unittest.TestCase):
    @patch("app.core.storage.get_settings")
    def test_get_asset_url_uses_cdn_base_when_configured(self, mock_get_settings) -> None:
        mock_get_settings.return_value = SimpleNamespace(
            storage_cdn_url="https://cdn.klarnow.ai/"
        )

        url = storage.get_asset_url("/logos/acme brand/logo final.png")

        self.assertEqual(
            url,
            "https://cdn.klarnow.ai/logos/acme%20brand/logo%20final.png",
        )

    @patch("app.core.storage.get_presigned_url")
    @patch("app.core.storage.get_settings")
    def test_get_asset_url_falls_back_to_presigned_url(
        self,
        mock_get_settings,
        mock_get_presigned_url,
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(storage_cdn_url="")
        mock_get_presigned_url.return_value = "https://signed.example.com/object"

        url = storage.get_asset_url("logos/acme/logo.png", expires_in=42)

        self.assertEqual(url, "https://signed.example.com/object")
        mock_get_presigned_url.assert_called_once_with("logos/acme/logo.png", expires_in=42)


if __name__ == "__main__":
    unittest.main()
