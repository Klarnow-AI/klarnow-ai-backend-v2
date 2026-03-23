from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-docs-module.db")

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.docs import routes as docs_routes
from app.modules.docs.composer import apply_section_action, compose_document
from app.modules.docs.registry import get_template_definition, list_template_definitions


def _dt() -> datetime:
    return datetime.now(timezone.utc)


def make_company_data(**overrides):
    payload = {
        "id": uuid4(),
        "pack_id": uuid4(),
        "business_name": "Acme Studio",
        "tagline": "Clean growth systems",
        "description": "We help businesses move from outreach to delivery.",
        "address": "London, UK",
        "phone": "+44 20 5555 1111",
        "email": "hello@acme.test",
        "website": "https://acme.test",
        "services": ["Strategy", "Execution"],
        "team_members": ["Ada - Founder"],
        "packages": ["Sprint package"],
        "standard_signatory": {"name": "Ada", "title": "Founder"},
        "standard_footer": "Acme Studio",
        "logo_url": None,
        "logo_markup": None,
        "brand_voice": "professional",
        "created_at": _dt(),
        "updated_at": _dt(),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def make_document(pack_id=None, **overrides):
    payload = {
        "id": uuid4(),
        "pack_id": pack_id or uuid4(),
        "created_by_user_id": uuid4(),
        "linked_document_id": None,
        "type": "proposal",
        "status": "generated",
        "title": "Proposal: Acme",
        "tone_preset": "professional",
        "start_mode": "template",
        "inputs_json": {"client_name": "Acme", "client_challenge": "Need a launch", "scope_of_work": "Launch support", "timeline": "2 weeks", "pricing_summary": "1500"},
        "source_context_json": {"missing_fields": [], "warnings": []},
        "export_meta_json": {},
        "created_at": _dt(),
        "updated_at": _dt(),
    }
    payload.update(overrides)
    section = SimpleNamespace(
        id=uuid4(),
        document_id=payload["id"],
        section_key="executive_summary",
        section_label="Executive Summary",
        content="A concise overview.",
        order_index=0,
        metadata_json=None,
        created_at=_dt(),
        updated_at=_dt(),
    )
    payload.setdefault("sections", [section])
    return SimpleNamespace(**payload)


class DocsRegistryTests(unittest.TestCase):
    def test_registry_contains_full_v1_document_set(self) -> None:
        definitions = {item.type: item for item in list_template_definitions()}

        self.assertEqual(
            set(definitions.keys()),
            {
                "proposal",
                "invoice",
                "company_profile",
                "meeting_summary",
                "follow_up_summary",
                "employment_letter",
                "sponsorship_letter",
            },
        )
        self.assertEqual(
            [section.label for section in definitions["proposal"].section_blueprint],
            [
                "Title",
                "Executive Summary",
                "Client Challenge",
                "Our Approach",
                "Scope of Work",
                "Deliverables",
                "Timeline",
                "Pricing",
                "Next Steps",
            ],
        )

    def test_meeting_summary_generation_extracts_from_notes(self) -> None:
        definition = get_template_definition("meeting_summary")
        result = compose_document(
            definition,
            inputs={"raw_notes": "Kickoff Call\nMarch 12, 2026 - Ada, Ben\nLaunch the new service\nDecision: begin next Monday\nAction: share proposal"},
            company_data={"business_name": "Acme Studio"},
            source_context={},
        )

        self.assertEqual(result.title, "Kickoff Call")
        self.assertTrue(any(section.section_key == "key_discussion_points" for section in result.sections))
        self.assertIn("Action: share proposal", result.inputs["key_discussion_points"])

    def test_section_action_shortens_text(self) -> None:
        shortened = apply_section_action(
            action="shorten",
            content="Sentence one. Sentence two. Sentence three.",
            regenerated_content="Regenerated text.",
        )

        self.assertEqual(shortened, "Sentence one. Sentence two.")


class DocsRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        main_module.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

        def _fake_db():
            yield SimpleNamespace()

        main_module.app.dependency_overrides[get_db] = _fake_db

    def tearDown(self) -> None:
        main_module.app.dependency_overrides.clear()

    def test_templates_route_returns_registry_payload(self) -> None:
        pack = SimpleNamespace(id=uuid4())
        home_payload = {
            "suggestions": [],
            "recent_documents": [],
            "templates": list_template_definitions(),
            "company_data": make_company_data(pack_id=pack.id),
            "document_counts": {},
        }

        with (
            patch.object(docs_routes, "get_pack_for_user", return_value=pack),
            patch.object(docs_routes, "build_docs_home", return_value=home_payload),
            TestClient(main_module.app, raise_server_exceptions=False) as client,
        ):
            response = client.get(f"/api/v1/packs/{pack.id}/docs/templates")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 7)
        self.assertEqual(response.json()[0]["label"], "Proposal")

    def test_generate_route_returns_document_payload(self) -> None:
        pack = SimpleNamespace(id=uuid4())
        document = make_document(pack_id=pack.id)

        with (
            patch.object(docs_routes, "get_pack_for_user", return_value=pack),
            patch.object(docs_routes, "get_document_for_pack_user", return_value=document),
            patch.object(docs_routes, "generate_document_draft", return_value=document),
            TestClient(main_module.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/api/v1/packs/{pack.id}/docs/documents/{document.id}/generate",
                json={},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Proposal: Acme")
        self.assertEqual(response.json()["sections"][0]["section_label"], "Executive Summary")

    def test_pdf_route_streams_pdf_bytes(self) -> None:
        pack = SimpleNamespace(id=uuid4())
        document = make_document(pack_id=pack.id, type="invoice", title="Invoice: Acme")

        with (
            patch.object(docs_routes, "get_pack_for_user", return_value=pack),
            patch.object(docs_routes, "get_document_for_pack_user", return_value=document),
            patch.object(docs_routes, "export_document_pdf", return_value=b"%PDF-1.4 test"),
            TestClient(main_module.app, raise_server_exceptions=False) as client,
        ):
            response = client.get(
                f"/api/v1/packs/{pack.id}/docs/documents/{document.id}/pdf"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("invoice-", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
