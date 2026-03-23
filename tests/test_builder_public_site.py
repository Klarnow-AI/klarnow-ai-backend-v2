from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-builder-public-site.db")

from app.modules.builder.public_site_schemas import normalize_public_lead_payload
from app.modules.builder.services import (
    build_deploy_html,
    build_site_shell_meta,
)
from app.shared.generation_schemas import (
    GenerationBrandContext,
    GenerationColorPalette,
)


class BuilderPublicSiteTests(unittest.TestCase):
    def test_normalize_public_lead_payload_supports_common_form_fields(self) -> None:
        body = normalize_public_lead_payload(
            {
                "fullName": "Ada Lovelace",
                "emailAddress": "ada@example.com",
                "message": "Need a landing page refresh",
                "company": "Analytical Engines",
                "budget": "5k-10k",
            }
        )

        self.assertEqual(body.name, "Ada Lovelace")
        self.assertEqual(body.email, "ada@example.com")
        self.assertIn("Need a landing page refresh", body.summary or "")
        self.assertIn("Company: Analytical Engines", body.summary or "")
        self.assertIn("Budget: 5k-10k", body.summary or "")

    def test_build_deploy_html_injects_lead_url_and_brand_shell_meta(self) -> None:
        html = build_deploy_html(
            {"/App.tsx": "export default function App() { return <main>Hello</main>; }"},
            project_id="proj-123",
            lead_url="/lead",
            site_title="Northstar Studio",
            favicon_href="https://cdn.example.com/logo.svg",
            theme_color="#111827",
        )

        self.assertIn("<title>Northstar Studio</title>", html)
        self.assertIn('window.KLARO_LEAD_URL="/lead"', html)
        self.assertIn('rel="icon" href="https://cdn.example.com/logo.svg"', html)
        self.assertIn('name="theme-color" content="#111827"', html)

    def test_build_site_shell_meta_uses_brand_logo_markup(self) -> None:
        meta = build_site_shell_meta(
            GenerationBrandContext(
                brand_name="Northstar Studio",
                logo_markup="<svg xmlns='http://www.w3.org/2000/svg'><rect width='16' height='16' fill='#000'/></svg>",
                color_palette=GenerationColorPalette(primary="#101828"),
            ),
            fallback_title="Fallback",
        )

        self.assertEqual(meta["site_title"], "Northstar Studio")
        self.assertTrue(meta["favicon_href"].startswith("data:image/svg+xml"))
        self.assertEqual(meta["theme_color"], "#101828")
