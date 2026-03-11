from __future__ import annotations

import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-creative-generation.db")

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.creative import routes as creative_routes
from app.modules.creative.generation import (
    PROOF_FALLBACK,
    SHARED_CREATIVE_SYSTEM_PROMPT,
    TEMPLATE_PROMPTS,
    VARIANT_INSTRUCTIONS,
    build_poster_system_prompt,
    resolve_poster_prompt_brief,
)
from app.shared.generation_schemas import GenerationBrandContext
from app.shared.services.generation_context import build_generation_brand_context


def make_pack(**overrides):
    defaults = {
        "id": uuid4(),
        "name": "Acme Pack",
        "brand_name": "Acme",
        "offer_one_liner": "Launch in 30 days",
        "primary_cta": "Book now",
        "usp_locked_line": "Launch with zero bottlenecks",
        "usp_statement": "Fast launch support",
        "usp_proof": "Trusted by 42 founders",
        "proof_text": "Trusted by 42 founders",
        "business_type": "service",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _required_filenames(prompt: str) -> list[str]:
    match = re.search(
        r"Return exactly these filenames:\n(?P<files>.*?)\n\nFILE RULES",
        prompt,
        re.DOTALL,
    )
    if not match:
        return []
    return [
        line.removeprefix("- ").strip()
        for line in match.group("files").strip().splitlines()
        if line.strip()
    ]


class PosterPromptAssemblyTests(unittest.TestCase):
    def test_manual_prompt_embeds_shared_creative_block_and_only_targets_v1_files(self) -> None:
        pack = make_pack()
        brand_context = GenerationBrandContext(
            core_offer="Brand OS offer",
            usp_statement="Brand OS USP",
            proof_points=["Brand OS proof"],
            voice_archetype="luxury",
        )

        prompt = build_poster_system_prompt(
            pack=pack,
            brand_context=brand_context,
            generation_mode="manual",
        )

        required_files = _required_filenames(prompt)

        self.assertIn(SHARED_CREATIVE_SYSTEM_PROMPT, prompt)
        self.assertIn(TEMPLATE_PROMPTS["offer"], prompt)
        self.assertIn(VARIANT_INSTRUCTIONS["A"], prompt)
        self.assertIn("CONCEPT SLOT MAPPING\n- v1: template=offer, variant=A", prompt)
        self.assertIn("BRAND: Acme", prompt)
        self.assertIn("OFFER: Launch in 30 days", prompt)
        self.assertIn('ONE CTA only: "Book now"', prompt)
        self.assertEqual(len(required_files), 4)
        self.assertIn("/poster-v1-4x5.tsx", required_files)
        self.assertNotIn("/poster-v2-4x5.tsx", required_files)

    def test_prompt_requires_exact_brand_logo_asset_when_logo_url_exists(self) -> None:
        prompt = build_poster_system_prompt(
            pack=make_pack(),
            brand_context=GenerationBrandContext(
                brand_name="Acme",
                logo_url="https://cdn.example.com/acme-logo.svg",
            ),
            generation_mode="manual",
        )

        self.assertIn("Logo URL: https://cdn.example.com/acme-logo.svg", prompt)
        self.assertIn(
            "must appear visibly in every generated poster/flyer file",
            prompt,
        )
        self.assertIn(
            'src="https://cdn.example.com/acme-logo.svg"',
            prompt,
        )
        self.assertIn('referrerPolicy="no-referrer"', prompt)

    def test_auto_prompt_uses_fixed_combo_mapping_and_targets_16_files(self) -> None:
        prompt = build_poster_system_prompt(
            pack=make_pack(),
            brand_context=GenerationBrandContext(),
            generation_mode="auto",
        )

        required_files = _required_filenames(prompt)

        self.assertIn("CONCEPT SLOT MAPPING", prompt)
        self.assertIn("- v1: template=objection, variant=A", prompt)
        self.assertIn("- v2: template=offer, variant=B", prompt)
        self.assertIn("- v3: template=proof, variant=C", prompt)
        self.assertIn("- v4: template=offer, variant=A", prompt)
        self.assertIn(TEMPLATE_PROMPTS["proof"], prompt)
        self.assertIn(VARIANT_INSTRUCTIONS["C"], prompt)
        self.assertEqual(len(required_files), 16)
        self.assertLess(prompt.index("- v1: template=objection, variant=A"), prompt.index("- v2: template=offer, variant=B"))
        self.assertLess(prompt.index("- v2: template=offer, variant=B"), prompt.index("- v3: template=proof, variant=C"))
        self.assertLess(prompt.index("- v3: template=proof, variant=C"), prompt.index("- v4: template=offer, variant=A"))

    def test_resolved_brief_uses_pack_and_brand_context_fallbacks(self) -> None:
        pack = make_pack(
            brand_name="",
            name="Fallback Pack",
            offer_one_liner="",
            primary_cta="",
            usp_locked_line="",
            proof_text="",
            business_type="",
            usp_statement="Pack USP statement",
            usp_proof="Pack USP proof",
        )
        brand_context = GenerationBrandContext(
            core_offer="Brand OS offer",
            usp_statement="Brand OS USP",
            proof_points=["12 case studies"],
            industry="agency",
            voice_archetype="luxury",
        )

        brief = resolve_poster_prompt_brief(pack=pack, brand_context=brand_context)

        self.assertEqual(brief.business_name, "Fallback Pack")
        self.assertEqual(brief.offer, "Brand OS offer")
        self.assertEqual(brief.usp, "Pack USP statement")
        self.assertEqual(brief.cta, "Learn more")
        self.assertEqual(brief.proof_line, 'Proof/testimonial: "12 case studies"')
        self.assertEqual(brief.business_type, "agency")
        self.assertEqual(brief.tone, "luxury")

    def test_resolved_brief_uses_exact_proof_fallback_when_no_proof_exists(self) -> None:
        brief = resolve_poster_prompt_brief(
            pack=make_pack(proof_text="", usp_proof=""),
            brand_context=GenerationBrandContext(proof_points=[]),
        )

        self.assertEqual(brief.proof_line, PROOF_FALLBACK)


class CreativeGenerationRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        main_module.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

        def _fake_db():
            yield SimpleNamespace()

        main_module.app.dependency_overrides[get_db] = _fake_db

    def tearDown(self) -> None:
        main_module.app.dependency_overrides.clear()

    def test_generate_route_rejects_empty_messages(self) -> None:
        with TestClient(main_module.app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/creative/generate",
                json={"packId": str(uuid4()), "messages": []},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Missing messages")

    def test_generate_route_streams_text_response(self) -> None:
        pack = make_pack()
        brand_context = GenerationBrandContext(brand_name="Acme")

        async def fake_stream(**kwargs):
            self.assertEqual(kwargs["pack"], pack)
            self.assertEqual(kwargs["brand_context"], brand_context)
            self.assertEqual(kwargs["generation_mode"], "manual")

            async def iterator():
                yield "<summary>Poster ready.</summary>"
                yield "<file name=\"/poster-v1-4x5.tsx\">export default function Poster(){return <div style={{width:1080,height:1350}} />}</file>"

            return iterator()

        with (
            patch.object(creative_routes, "get_pack_for_user", return_value=pack),
            patch.object(creative_routes, "can_generate_assets", return_value=None),
            patch.object(creative_routes, "load_generation_brand_context", return_value=brand_context),
            patch.object(creative_routes, "create_poster_generation_stream", side_effect=fake_stream),
            TestClient(main_module.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/api/v1/creative/generate",
                json={
                    "packId": str(pack.id),
                    "messages": [{"role": "user", "content": "Make me a poster"}],
                    "generationMode": "manual",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertIn("<summary>Poster ready.</summary>", response.text)


class GenerationContextLogoTests(unittest.TestCase):
    def test_build_generation_brand_context_preserves_logo_url(self) -> None:
        pack = SimpleNamespace(
            onboarding_answers={"wordmark_svg_or_url": "https://cdn.example.com/logo.svg"},
            brand_name="Acme",
            offer_one_liner=None,
            primary_cta=None,
            primary_pain=None,
            primary_outcome=None,
            hero_angle=None,
            usp_statement=None,
            usp_proof=None,
        )

        context = build_generation_brand_context(pack)

        self.assertEqual(context.logo_url, "https://cdn.example.com/logo.svg")
        self.assertIsNone(context.logo_markup)

    def test_build_generation_brand_context_preserves_inline_svg_wordmark(self) -> None:
        svg_markup = "<svg viewBox='0 0 10 10'><path d='M0 0h10v10H0z' /></svg>"
        pack = SimpleNamespace(
            onboarding_answers={"wordmark_svg_or_url": svg_markup},
            brand_name="Acme",
            offer_one_liner=None,
            primary_cta=None,
            primary_pain=None,
            primary_outcome=None,
            hero_angle=None,
            usp_statement=None,
            usp_proof=None,
        )

        context = build_generation_brand_context(pack)

        self.assertIsNone(context.logo_url)
        self.assertEqual(context.logo_markup, svg_markup)


if __name__ == "__main__":
    unittest.main()
