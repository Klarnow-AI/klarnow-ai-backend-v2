from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.modules.sprint.day_readiness import get_day_readiness_state, is_day_ready_to_complete


def _db_for_pack(pack) -> Mock:
    filtered = Mock()
    filtered.first.return_value = pack

    query = Mock()
    query.filter.return_value = filtered

    db = Mock()
    db.query.return_value = query
    return db


class DayReadinessTests(unittest.TestCase):
    def test_get_day_readiness_state_returns_reason_for_missing_required_field(self) -> None:
        pack = SimpleNamespace(
            onboarding_answers={"has_existing_brand": "no"},
            brand_name="Acme",
            primary_cta="Book a call",
            usp_category="Faster",
            usp_statement="We launch in 48 hours",
            website_url=None,
            offer_one_liner="We help founders ship faster",
            primary_pain="",
            primary_outcome="More qualified leads",
            pitch_script=None,
            voice_notes_sent=None,
        )

        state = get_day_readiness_state(_db_for_pack(pack), uuid4(), 2)

        self.assertEqual(
            state,
            {
                "ready": False,
                "reason": 'Please complete "What\'s the primary pain point?" before finishing Step 2.',
            },
        )

    def test_is_day_ready_to_complete_skips_brand_url_for_new_brands(self) -> None:
        pack = SimpleNamespace(
            onboarding_answers={"has_existing_brand": "no"},
            brand_name="Acme",
            primary_cta="Book a call",
            usp_category="Faster",
            usp_statement="We launch in 48 hours",
            website_url=None,
            offer_one_liner=None,
            primary_pain=None,
            primary_outcome=None,
            pitch_script=None,
            voice_notes_sent=None,
        )

        ready = is_day_ready_to_complete(_db_for_pack(pack), uuid4(), 0)

        self.assertTrue(ready)


if __name__ == "__main__":
    unittest.main()
