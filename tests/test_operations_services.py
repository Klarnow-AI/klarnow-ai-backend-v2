from __future__ import annotations

import unittest

from app.modules.operations.models import (
    ACTION_MODE_APPROVAL,
    ACTION_MODE_EXTERNAL_DISPATCH,
    COMMERCIAL_SENSITIVITY_REVENUE,
    COMMERCIAL_SENSITIVITY_SAFE,
    PRIORITY_IMPORTANT,
    PRIORITY_URGENT,
    RESPONSE_MODE_APPROVAL,
    RESPONSE_MODE_SUGGESTED,
)
from app.modules.operations.services import derive_policy_for_activity


class OperationsPolicyTests(unittest.TestCase):
    def test_discount_request_requires_approval(self) -> None:
        policy = derive_policy_for_activity("discount_request")

        self.assertTrue(policy["requires_approval"])
        self.assertEqual(policy["priority"], PRIORITY_IMPORTANT)
        self.assertEqual(
            policy["commercial_sensitivity"],
            COMMERCIAL_SENSITIVITY_REVENUE,
        )
        self.assertEqual(policy["response_mode"], RESPONSE_MODE_APPROVAL)
        self.assertEqual(policy["action_mode"], ACTION_MODE_APPROVAL)

    def test_new_lead_prepares_external_dispatch(self) -> None:
        policy = derive_policy_for_activity("new_lead")

        self.assertFalse(policy["requires_approval"])
        self.assertEqual(policy["priority"], PRIORITY_IMPORTANT)
        self.assertEqual(
            policy["commercial_sensitivity"],
            COMMERCIAL_SENSITIVITY_SAFE,
        )
        self.assertEqual(policy["response_mode"], RESPONSE_MODE_SUGGESTED)
        self.assertEqual(policy["action_mode"], ACTION_MODE_EXTERNAL_DISPATCH)

    def test_missed_lead_followup_is_urgent(self) -> None:
        policy = derive_policy_for_activity("missed_lead_followup")

        self.assertEqual(policy["priority"], PRIORITY_URGENT)
        self.assertFalse(policy["requires_approval"])
        self.assertEqual(policy["response_mode"], RESPONSE_MODE_SUGGESTED)
        self.assertEqual(policy["action_mode"], ACTION_MODE_EXTERNAL_DISPATCH)


if __name__ == "__main__":
    unittest.main()
