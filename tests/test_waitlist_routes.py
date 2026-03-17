from __future__ import annotations

import os
import unittest

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
        self.assertEqual(
            signups[0].goal,
            "Generate better campaigns, improve follow-up, and turn more interest into customers.",
        )
        self.assertEqual(signups[0].source, "landing-page-beta")

    def test_subscribe_is_idempotent_for_existing_email(self) -> None:
        with TestClient(main_module.app, raise_server_exceptions=False) as client:
            first = client.post(
                "/api/v1/waitlist/subscribe",
                json={
                    "firstName": "Ada",
                    "email": "founder@example.com",
                    "role": "Consultant or agency",
                    "goal": "Get more leads",
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
                    "goal": "Turn more interest into customers.",
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
        self.assertEqual(signups[0].goal, "Turn more interest into customers.")
        self.assertEqual(signups[0].source, "homepage-hero")

    def test_subscribe_rejects_honeypot_submissions(self) -> None:
        with TestClient(main_module.app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/waitlist/subscribe",
                json={
                    "firstName": "Ada",
                    "email": "founder@example.com",
                    "role": "Consultant or agency",
                    "goal": "Get more leads",
                    "source": "landing-page-beta",
                    "website": "https://spam.example",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self._all_signups()), 0)


if __name__ == "__main__":
    unittest.main()
