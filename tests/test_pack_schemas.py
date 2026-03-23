from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch

from app.modules.packs.schemas import PackRead


class PackReadSchemaTests(unittest.TestCase):
    @patch("app.modules.packs.schemas.resolve_asset_reference")
    def test_pack_read_normalizes_stored_onboarding_asset_urls(self, mock_resolve_asset_reference) -> None:
        mock_resolve_asset_reference.side_effect = (
            lambda value, expires_in=0: f"resolved::{value}" if isinstance(value, str) else value
        )

        pack = PackRead.model_validate(
            {
                "id": str(uuid4()),
                "name": "Acme",
                "status": "draft",
                "pack_type": "enquiries",
                "onboarding_answers": {
                    "wordmark_svg_or_url": "https://cdn.klarnow.ai/logos/acme/logo.png",
                    "wordmark_result": "key:logos/acme/alt.png",
                    "generated_logo_url": "key:logos/acme/default.webp",
                    "transparent_logo_url": "key:logos/acme/transparent.png",
                    "suggested_logos": json.dumps(
                        [
                            "https://cdn.klarnow.ai/logos/acme/one.png",
                            "<svg>inline</svg>",
                        ]
                    ),
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "created_by_user_id": str(uuid4()),
            }
        )

        onboarding = pack.onboarding_answers or {}
        self.assertEqual(
            onboarding["wordmark_svg_or_url"],
            "resolved::https://cdn.klarnow.ai/logos/acme/logo.png",
        )
        self.assertEqual(onboarding["wordmark_result"], "resolved::key:logos/acme/alt.png")
        self.assertEqual(
            onboarding["generated_logo_url"],
            "resolved::key:logos/acme/default.webp",
        )
        self.assertEqual(
            onboarding["transparent_logo_url"],
            "resolved::key:logos/acme/transparent.png",
        )
        self.assertEqual(
            json.loads(onboarding["suggested_logos"]),
            [
                "resolved::https://cdn.klarnow.ai/logos/acme/one.png",
                "resolved::<svg>inline</svg>",
            ],
        )


if __name__ == "__main__":
    unittest.main()
