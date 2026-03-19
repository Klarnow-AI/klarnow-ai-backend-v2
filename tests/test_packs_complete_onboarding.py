from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-packs-complete-onboarding.db")

from app.modules.packs import routes as packs_routes
from app.modules.packs.schemas import PackRead


class CompleteOnboardingRouteTests(unittest.TestCase):
    def test_complete_onboarding_reads_brand_os_id_from_tool_payload(self) -> None:
        pack_id = uuid4()
        user_id = uuid4()
        brand_os_id = uuid4()
        now = datetime.now(timezone.utc)
        pack = SimpleNamespace(
            id=pack_id,
            name="Project Career",
            status="draft",
            pack_type="enquiries",
            onboarding_answers={"has_existing_brand": "yes"},
            onboarding_completed_at=None,
            onboarding_background_completed_at=None,
            core_concept=None,
            created_at=now,
            updated_at=now,
            created_by_user_id=user_id,
            client_id=None,
            brand_name="Project Career",
            primary_cta=None,
            usp_category=None,
            usp_statement=None,
            usp_proof=None,
            usp_locked_line=None,
            proof_types=None,
            proof_text=None,
            day_0_completed_at=None,
            offer_one_liner=None,
            target_audience=None,
            primary_pain=None,
            primary_outcome=None,
            hero_angle=None,
        )
        pack_read = PackRead.model_validate(pack)
        db = SimpleNamespace(commit=MagicMock(), refresh=MagicMock())
        current_user = SimpleNamespace(id=user_id)
        brand_os_row = SimpleNamespace(id=brand_os_id, version="A")

        def fake_complete_onboarding(_db, pack_arg, answers, commit=False):
            del answers, commit
            pack_arg.onboarding_completed_at = now
            return pack_arg

        with (
            patch.object(packs_routes, "get_pack_for_user", return_value=pack),
            patch.object(packs_routes, "_require_step_2_finalization_ready"),
            patch.object(packs_routes, "sync_pack_target_audience"),
            patch.object(packs_routes, "build_step_2_finalization_payload", return_value={"a": 1}),
            patch.object(packs_routes, "fingerprint_payload", return_value="fingerprint"),
            patch.object(packs_routes, "get_step_2_finalization_cache", return_value={}),
            patch.object(packs_routes, "get_brand_os_by_source_job_id", return_value=None),
            patch.object(
                packs_routes,
                "generate_brand_os",
                return_value={"brand_os_id": str(brand_os_id), "version": "A"},
            ),
            patch.object(
                packs_routes,
                "get_brand_os_by_id_and_pack",
                return_value=brand_os_row,
            ) as mock_get_brand_os,
            patch.object(packs_routes, "set_step_2_finalization_cache"),
            patch.object(packs_routes, "complete_onboarding", side_effect=fake_complete_onboarding),
            patch.object(packs_routes.PackRead, "model_validate", return_value=pack_read),
            patch.object(packs_routes, "brand_os_read_from_orm", return_value=None) as mock_brand_os_read,
        ):
            response = packs_routes.complete_onboarding_route(
                pack_id=pack_id,
                db=db,
                current_user=current_user,
            )

        self.assertTrue(response.is_existing_brand)
        self.assertEqual(response.pack.id, pack_id)
        mock_get_brand_os.assert_called_once_with(db, brand_os_id, pack_id)
        mock_brand_os_read.assert_called_once_with(brand_os_row)


if __name__ == "__main__":
    unittest.main()
