from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core import storage


class GetAssetUrlTests(unittest.TestCase):
    def setUp(self) -> None:
        storage._CDN_FAILURE_UNTIL_BY_BASE.clear()

    @patch("app.core.storage.requests.head")
    @patch("app.core.storage.get_settings")
    def test_get_asset_url_uses_cdn_base_when_probe_succeeds(
        self,
        mock_get_settings,
        mock_head,
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(
            storage_cdn_url="https://cdn.klarnow.ai/"
        )
        mock_head.return_value = Mock(status_code=200)

        url = storage.get_asset_url("/logos/acme brand/logo final.png")

        self.assertEqual(
            url,
            "https://cdn.klarnow.ai/logos/acme%20brand/logo%20final.png",
        )
        mock_head.assert_called_once_with(
            "https://cdn.klarnow.ai/logos/acme%20brand/logo%20final.png",
            allow_redirects=True,
            timeout=storage.CDN_PROBE_TIMEOUT_SECONDS,
        )

    @patch("app.core.storage.requests.head")
    @patch("app.core.storage.get_presigned_url")
    @patch("app.core.storage.get_settings")
    def test_get_asset_url_falls_back_to_presigned_url(
        self,
        mock_get_settings,
        mock_get_presigned_url,
        mock_head,
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(storage_cdn_url="")
        mock_get_presigned_url.return_value = "https://signed.example.com/object"

        url = storage.get_asset_url("logos/acme/logo.png", expires_in=42)

        self.assertEqual(url, "https://signed.example.com/object")
        mock_get_presigned_url.assert_called_once_with("logos/acme/logo.png", expires_in=42)
        mock_head.assert_not_called()

    @patch("app.core.storage.requests.head")
    @patch("app.core.storage.get_presigned_url")
    @patch("app.core.storage.get_settings")
    def test_get_asset_url_falls_back_to_presigned_url_when_cdn_probe_fails(
        self,
        mock_get_settings,
        mock_get_presigned_url,
        mock_head,
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(
            storage_cdn_url="https://cdn.klarnow.ai"
        )
        mock_get_presigned_url.return_value = "https://signed.example.com/object"
        mock_head.return_value = Mock(status_code=404)

        url = storage.get_asset_url("logos/acme/logo.png", expires_in=42)

        self.assertEqual(url, "https://signed.example.com/object")
        mock_get_presigned_url.assert_called_once_with("logos/acme/logo.png", expires_in=42)


if __name__ == "__main__":
    unittest.main()
