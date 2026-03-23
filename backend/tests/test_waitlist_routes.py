from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-waitlist-routes.db")
os.environ["DB_CONNECT_TIMEOUT_SECONDS"] = "0"
os.environ["FAILURE_ALERT_TO_EMAIL"] = ""
os.environ["RESEND_API_KEY"] = ""
os.environ["SUPPORT_EMAIL"] = ""

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.db.session import SessionLocal, engine
from app.modules.waitlist.models import WaitlistSignup


class WaitlistRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        WaitlistSignup.__table__.create(bind=engine, checkfirst=True)

    @classmethod
    def tearDownClass(cls) -> None:
        WaitlistSignup.__table__.drop(bind=engine, checkfirst=True)
        db_path = "test-waitlist-routes.db"
        if os.path.exists(db_path):
            os.remove(db_path)

    def setUp(self) -> None:
        WaitlistSignup.__table__.drop(bind=engine, checkfirst=True)
        WaitlistSignup.__table__.create(bind=engine, checkfirst=True)

    def _all_signups(self) -> list[WaitlistSignup]:
        with SessionLocal() as db:
            return db.query(WaitlistSignup).order_by(WaitlistSignup.created_at).all()

    def test_subscribe_sends_team_notification_for_new_signup(self) -> None:
        fake_resend = SimpleNamespace(Emails=SimpleNamespace(send=Mock()))
        original_api_key = main_module.settings.resend_api_key
        original_from_email = main_module.settings.resend_from_email
        original_to_email = main_module.settings.waitlist_notification_to_email
        main_module.settings.resend_api_key = "re_test"
        main_module.settings.resend_from_email = "noreply@example.com"
        main_module.settings.waitlist_notification_to_email = "team@klarnow.co.uk"
        try:
            with patch.dict(sys.modules, {"resend": fake_resend}):
                with TestClient(main_module.app, raise_server_exceptions=False) as client:
                    response = client.post(
                        "/api/v1/waitlist/subscribe",
                        json={
                            "firstName": "Ada",
                            "email": "Ada@business.com",
                            "role": "Consultant or agency",
                            "source": "landing-page-beta",
                            "website": "",
                        },
                    )
        finally:
            main_module.settings.resend_api_key = original_api_key
            main_module.settings.resend_from_email = original_from_email
            main_module.settings.waitlist_notification_to_email = original_to_email

        self.assertEqual(response.status_code, 201)
        fake_resend.Emails.send.assert_called_once()
        payload = fake_resend.Emails.send.call_args.args[0]
        self.assertEqual(payload["to"], "team@klarnow.co.uk")
        self.assertEqual(payload["from"], "noreply@example.com")
        self.assertEqual(payload["subject"], "New Klarnow waitlist signup")
        self.assertIn("Ada@business.com".lower(), payload["html"].lower())

    def test_subscribe_does_not_send_duplicate_team_notification(self) -> None:
        fake_resend = SimpleNamespace(Emails=SimpleNamespace(send=Mock()))
        original_api_key = main_module.settings.resend_api_key
        original_from_email = main_module.settings.resend_from_email
        original_to_email = main_module.settings.waitlist_notification_to_email
        main_module.settings.resend_api_key = "re_test"
        main_module.settings.resend_from_email = "noreply@example.com"
        main_module.settings.waitlist_notification_to_email = "team@klarnow.co.uk"
        try:
            with patch.dict(sys.modules, {"resend": fake_resend}):
                with TestClient(main_module.app, raise_server_exceptions=False) as client:
                    first = client.post(
                        "/api/v1/waitlist/subscribe",
                        json={
                            "firstName": "Ada",
                            "email": "founder@example.com",
                            "role": "Consultant or agency",
                            "source": "landing-page-beta",
                            "website": "",
                        },
                    )
                    second = client.post(
                        "/api/v1/waitlist/subscribe",
                        json={
                            "firstName": "Ada Lovelace",
                            "email": "FOUNDER@example.com",
                            "role": "In-house marketer",
                            "source": "homepage-hero",
                            "website": "",
                        },
                    )
        finally:
            main_module.settings.resend_api_key = original_api_key
            main_module.settings.resend_from_email = original_from_email
            main_module.settings.waitlist_notification_to_email = original_to_email

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        fake_resend.Emails.send.assert_called_once()

    def test_subscribe_creates_waitlist_signup(self) -> None:
        with TestClient(main_module.app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/waitlist/subscribe",
                json={
                    "firstName": "Ada",
                    "email": "Ada@business.com",
                    "role": "Consultant or agency",
                    "goal": "Generate better campaigns, improve follow-up, and turn more interest into customers.",
                    "source": "landing-page-beta",
                    "website": "",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "subscribed",
                "already_subscribed": False,
            },
        )

        signups = self._all_signups()
        self.assertEqual(len(signups), 1)
        self.assertEqual(signups[0].email, "ada@business.com")
        self.assertEqual(signups[0].first_name, "Ada")
        self.assertEqual(signups[0].role, "Consultant or agency")
        self.assertIsNone(signups[0].goal)
        self.assertEqual(signups[0].source, "landing-page-beta")

    def test_subscribe_is_idempotent_for_existing_email(self) -> None:
        with TestClient(main_module.app, raise_server_exceptions=False) as client:
            first = client.post(
                "/api/v1/waitlist/subscribe",
                json={
                    "firstName": "Ada",
                    "email": "founder@example.com",
                    "role": "Consultant or agency",
                    "source": "landing-page-beta",
                    "website": "",
                },
            )
            second = client.post(
                "/api/v1/waitlist/subscribe",
                json={
                    "firstName": "Ada Lovelace",
                    "email": "FOUNDER@example.com",
                    "role": "In-house marketer",
                    "source": "homepage-hero",
                    "website": "",
                },
            )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            second.json(),
            {
                "status": "subscribed",
                "already_subscribed": True,
            },
        )

        signups = self._all_signups()
        self.assertEqual(len(signups), 1)
        self.assertEqual(signups[0].email, "founder@example.com")
        self.assertEqual(signups[0].first_name, "Ada Lovelace")
        self.assertEqual(signups[0].role, "In-house marketer")
        self.assertIsNone(signups[0].goal)
        self.assertEqual(signups[0].source, "homepage-hero")

    def test_subscribe_rejects_honeypot_submissions(self) -> None:
        with TestClient(main_module.app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/waitlist/subscribe",
                json={
                    "firstName": "Ada",
                    "email": "founder@example.com",
                    "role": "Consultant or agency",
                    "source": "landing-page-beta",
                    "website": "https://spam.example",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self._all_signups()), 0)


if __name__ == "__main__":
    unittest.main()
