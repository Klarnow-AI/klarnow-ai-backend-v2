from __future__ import annotations

import json
import os
import unittest
import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-logo-generation.db")

from PIL import Image
from fastapi.testclient import TestClient

from app import main as main_module
from app.core.auth.deps import get_current_user
from app.core.config import Settings
from app.core.db.session import get_db
from app.core.errors import BadRequestError
from app.modules.packs import onboarding_jobs
from app.modules.packs import logo_generation
from app.modules.packs import routes as packs_routes
from app.modules.packs.onboarding_services import generate_starter_brand


class SettingsAliasTests(unittest.TestCase):
    def test_openrouter_api_key_is_loaded(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "sqlite:///./settings-alias-test.db",
                "OPENROUTER_API_KEY": "router-key",
            },
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.openrouter_api_key, "router-key")


class LogoGenerationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        logo_generation._PROVIDER_FAILURE_STATE["until"] = 0.0
        logo_generation._PROVIDER_FAILURE_STATE["reason"] = ""

    def tearDown(self) -> None:
        logo_generation._PROVIDER_FAILURE_STATE["until"] = 0.0
        logo_generation._PROVIDER_FAILURE_STATE["reason"] = ""

    def test_generate_logo_with_openrouter_uploads_image_and_uses_configured_model(self) -> None:
        source = BytesIO()
        Image.new("RGB", (8, 8), "white").save(source, format="PNG")
        source_bytes = source.getvalue()
        encoded = "data:image/webp;base64," + base64.b64encode(source_bytes).decode("ascii")
        fake_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        images=[SimpleNamespace(image_url=SimpleNamespace(url=encoded))]
                    )
                )
            ]
        )
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=MagicMock(return_value=fake_response))
            )
        )

        with (
            patch.object(
                logo_generation,
                "get_settings",
                return_value=SimpleNamespace(ai_logo_generation_enabled=True),
            ),
            patch.object(logo_generation, "has_openai_compatible_provider", return_value=True),
            patch.object(logo_generation, "create_sync_openai_client", return_value=fake_client),
            patch.object(logo_generation, "get_logo_model", return_value="google/gemini-image-custom"),
            patch.object(logo_generation, "upload_file", return_value="stored-key") as mock_upload,
            patch.object(
                logo_generation,
                "get_asset_url",
                side_effect=[
                    "https://cdn.example.com/generated-logo.webp",
                    "https://cdn.example.com/generated-logo-transparent.png",
                ],
            ),
        ):
            result = logo_generation.generate_logo_with_openrouter("Make a bold logo", "pack-123")

        self.assertEqual(
            result,
            {
                "logo_url": "https://cdn.example.com/generated-logo.webp",
                "wordmark_svg_or_url": "https://cdn.example.com/generated-logo-transparent.png",
                "transparent_logo_url": "https://cdn.example.com/generated-logo-transparent.png",
            },
        )
        generate_call = fake_client.chat.completions.create.call_args.kwargs
        self.assertEqual(generate_call["model"], "google/gemini-image-custom")
        self.assertEqual(generate_call["messages"], [{"role": "user", "content": "Make a bold logo"}])
        self.assertEqual(generate_call["extra_body"]["modalities"], ["image", "text"])
        self.assertEqual(generate_call["extra_body"]["image_config"]["aspect_ratio"], "1:1")
        self.assertEqual(generate_call["extra_body"]["image_config"]["image_size"], "1K")
        self.assertEqual(mock_upload.call_count, 2)
        default_upload_call = mock_upload.call_args_list[0]
        transparent_upload_call = mock_upload.call_args_list[1]
        self.assertTrue(default_upload_call.args[0].startswith("logos/pack-123/"))
        self.assertTrue(default_upload_call.args[0].endswith(".webp"))
        self.assertEqual(default_upload_call.args[1], source_bytes)
        self.assertEqual(default_upload_call.kwargs["content_type"], "image/webp")
        self.assertTrue(transparent_upload_call.args[0].endswith("_transparent.png"))
        self.assertEqual(transparent_upload_call.kwargs["content_type"], "image/png")

    def test_generate_logo_with_openrouter_rejects_missing_image_parts(self) -> None:
        fake_response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(images=[]))])
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=MagicMock(return_value=fake_response))
            )
        )

        with (
            patch.object(
                logo_generation,
                "get_settings",
                return_value=SimpleNamespace(ai_logo_generation_enabled=True),
            ),
            patch.object(logo_generation, "has_openai_compatible_provider", return_value=True),
            patch.object(logo_generation, "create_sync_openai_client", return_value=fake_client),
            patch.object(logo_generation, "upload_file") as mock_upload,
        ):
            with self.assertRaises(BadRequestError) as exc_info:
                logo_generation.generate_logo_with_openrouter("Make a logo", "pack-123")

        self.assertIn("did not return an image", str(exc_info.exception).lower())
        mock_upload.assert_not_called()

    def test_generate_logo_with_openrouter_retries_with_image_only_when_modalities_are_wrong(self) -> None:
        class FakeModalitiesError(Exception):
            def __init__(self) -> None:
                super().__init__(
                    "{'error': {'message': 'No endpoints found that support the requested output modalities: image, text', 'code': 404}}"
                )

        source = BytesIO()
        Image.new("RGB", (8, 8), "white").save(source, format="PNG")
        source_bytes = source.getvalue()
        encoded = "data:image/png;base64," + base64.b64encode(source_bytes).decode("ascii")
        fake_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        images=[SimpleNamespace(image_url=SimpleNamespace(url=encoded))]
                    )
                )
            ]
        )
        create_mock = MagicMock(side_effect=[FakeModalitiesError(), fake_response])
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create_mock)
            )
        )

        with (
            patch.object(
                logo_generation,
                "get_settings",
                return_value=SimpleNamespace(ai_logo_generation_enabled=True),
            ),
            patch.object(logo_generation, "has_openai_compatible_provider", return_value=True),
            patch.object(logo_generation, "create_sync_openai_client", return_value=fake_client),
            patch.object(logo_generation, "get_logo_model", return_value="custom/experimental-image-model"),
            patch.object(logo_generation, "upload_file", return_value="stored-key") as mock_upload,
            patch.object(
                logo_generation,
                "get_asset_url",
                side_effect=[
                    "https://cdn.example.com/generated-logo.png",
                    "https://cdn.example.com/generated-logo-transparent.png",
                ],
            ),
        ):
            result = logo_generation.generate_logo_with_openrouter("Make a bold logo", "pack-123")

        self.assertEqual(
            result,
            {
                "logo_url": "https://cdn.example.com/generated-logo.png",
                "wordmark_svg_or_url": "https://cdn.example.com/generated-logo-transparent.png",
                "transparent_logo_url": "https://cdn.example.com/generated-logo-transparent.png",
            },
        )
        self.assertEqual(create_mock.call_count, 2)
        first_call = create_mock.call_args_list[0].kwargs
        second_call = create_mock.call_args_list[1].kwargs
        self.assertEqual(first_call["extra_body"]["modalities"], ["image", "text"])
        self.assertEqual(second_call["extra_body"]["modalities"], ["image"])
        default_upload_call = mock_upload.call_args_list[0]
        self.assertEqual(default_upload_call.args[1], source_bytes)
        self.assertEqual(default_upload_call.kwargs["content_type"], "image/png")

    def test_generate_logo_with_openrouter_sets_cooldown_for_quota_errors(self) -> None:
        class FakeQuotaError(Exception):
            def __init__(self) -> None:
                super().__init__("quota exceeded")
                self.code = 429
                self.status = "RESOURCE_EXHAUSTED"
                self.message = "Quota exceeded"
                self.details = {"error": {"message": "Quota exceeded"}}

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=MagicMock(side_effect=FakeQuotaError()))
            )
        )

        with (
            patch.object(
                logo_generation,
                "get_settings",
                return_value=SimpleNamespace(ai_logo_generation_enabled=True),
            ),
            patch.object(logo_generation, "has_openai_compatible_provider", return_value=True),
            patch.object(logo_generation, "create_sync_openai_client", return_value=fake_client),
        ):
            with self.assertRaises(BadRequestError) as exc_info:
                logo_generation.generate_logo_with_openrouter("Make a logo", "pack-123")

        self.assertIn("quota or billing", str(exc_info.exception).lower())
        self.assertIsNotNone(logo_generation._get_provider_cooldown_reason())

    def test_generate_logo_returns_empty_result_in_non_strict_mode_after_provider_error(self) -> None:
        with (
            patch.object(
                logo_generation,
                "get_settings",
                return_value=SimpleNamespace(ai_logo_generation_enabled=True),
            ),
            patch.object(logo_generation, "has_openai_compatible_provider", return_value=True),
            patch.object(
                logo_generation,
                "generate_logo_with_openrouter",
                side_effect=BadRequestError("provider failed"),
            ),
        ):
            result = logo_generation.generate_logo(
                brand_name="Acme",
                prompt="memorable",
                pack_id="pack-123",
                strict=False,
            )

        self.assertEqual(
            result,
            {
                "logo_url": None,
                "wordmark_svg_or_url": None,
                "transparent_logo_url": None,
            },
        )

    def test_create_transparent_png_variant_removes_connected_background(self) -> None:
        image = Image.new("RGB", (12, 12), "white")
        for x in range(3, 9):
            for y in range(3, 9):
                image.putpixel((x, y), (0, 0, 0))

        source = BytesIO()
        image.save(source, format="PNG")

        variant_bytes = logo_generation._create_transparent_png_variant(source.getvalue())
        with Image.open(BytesIO(variant_bytes)) as variant_image:
            rgba = variant_image.convert("RGBA")
            self.assertEqual(rgba.getpixel((0, 0))[3], 0)
            self.assertEqual(rgba.getpixel((5, 5))[3], 255)

    def test_build_logo_prompt_makes_brand_palette_a_hard_visual_constraint(self) -> None:
        prompt = logo_generation._build_logo_prompt(
            brand_name="Acme",
            prompt="minimal but premium",
            color_scheme=None,
            brand_os_summary=None,
            color_palette={
                "primary": "#112233",
                "secondary": "#445566",
                "accent": "#778899",
            },
        )

        self.assertIn("Infuse these exact brand colors", prompt)
        self.assertIn("primary #112233", prompt)
        self.assertIn("secondary #445566", prompt)
        self.assertIn("accent #778899", prompt)
        self.assertIn("do not swap them for unrelated accent colors", prompt)


class GenerateLogoRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = SimpleNamespace(commit=MagicMock())
        main_module.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

        def _fake_db():
            yield self.db

        main_module.app.dependency_overrides[get_db] = _fake_db

    def tearDown(self) -> None:
        main_module.app.dependency_overrides.clear()

    def test_generate_logo_route_appends_generated_logo_to_suggested_logos(self) -> None:
        pack = SimpleNamespace(id=uuid4(), onboarding_answers={})

        with (
            patch.object(packs_routes, "get_pack_for_user", return_value=pack),
            patch.object(
                packs_routes,
                "generate_logo",
                return_value={
                    "logo_url": "https://cdn.example.com/generated-logo.png",
                    "wordmark_svg_or_url": "https://cdn.example.com/generated-logo-transparent.png",
                    "transparent_logo_url": "https://cdn.example.com/generated-logo-transparent.png",
                },
            ),
            TestClient(main_module.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/api/v1/packs/{pack.id}/onboarding/generate-logo",
                json={"brand_name": "Acme"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["logo_url"],
            "https://cdn.example.com/generated-logo.png",
        )
        self.assertEqual(
            response.json()["transparent_logo_url"],
            "https://cdn.example.com/generated-logo-transparent.png",
        )
        self.assertEqual(
            json.loads(pack.onboarding_answers["suggested_logos"]),
            [
                "https://cdn.example.com/generated-logo.png",
                "https://cdn.example.com/generated-logo-transparent.png",
            ],
        )
        self.assertEqual(
            pack.onboarding_answers["generated_logo_url"],
            "https://cdn.example.com/generated-logo.png",
        )
        self.assertEqual(
            pack.onboarding_answers["transparent_logo_url"],
            "https://cdn.example.com/generated-logo-transparent.png",
        )
        self.db.commit.assert_called_once()

    def test_generate_logo_route_falls_back_to_saved_pack_palette(self) -> None:
        pack = SimpleNamespace(
            id=uuid4(),
            onboarding_answers={
                "palette": json.dumps(
                    {
                        "primary": "#111111",
                        "secondary": "#222222",
                        "accent": "#333333",
                    }
                )
            },
        )

        with (
            patch.object(packs_routes, "get_pack_for_user", return_value=pack),
            patch.object(
                packs_routes,
                "generate_logo",
                return_value={
                    "logo_url": "https://cdn.example.com/generated-logo.png",
                    "wordmark_svg_or_url": "https://cdn.example.com/generated-logo-transparent.png",
                    "transparent_logo_url": "https://cdn.example.com/generated-logo-transparent.png",
                },
            ) as mock_generate_logo,
            TestClient(main_module.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                f"/api/v1/packs/{pack.id}/onboarding/generate-logo",
                json={"brand_name": "Acme"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_generate_logo.call_args.kwargs["color_palette"],
            {
                "primary": "#111111",
                "secondary": "#222222",
                "accent": "#333333",
            },
        )


class StarterBrandGenerationTests(unittest.TestCase):
    def test_generate_starter_brand_uses_shared_logo_generation_result(self) -> None:
        palette = {"primary": "#111111", "secondary": "#222222", "accent": "#333333"}

        with (
            patch(
                "app.modules.packs.onboarding_services._call_openai_palette",
                return_value=palette,
            ),
            patch(
                "app.modules.packs.logo_generation.generate_logo",
                return_value={
                    "logo_url": "https://cdn.example.com/starter-logo.png",
                    "wordmark_svg_or_url": "https://cdn.example.com/starter-logo-transparent.png",
                    "transparent_logo_url": "https://cdn.example.com/starter-logo-transparent.png",
                },
            ) as mock_generate_logo,
        ):
            result = generate_starter_brand(
                brand_name="Acme",
                vibe_chips=["bold", "modern"],
                onboarding_context={"offer": "Launch fast"},
                pack_id="pack-123",
            )

        self.assertEqual(
            result["wordmark_svg_or_url"],
            "https://cdn.example.com/starter-logo-transparent.png",
        )
        self.assertEqual(result["palette"], palette)
        self.assertEqual(result["logo_url"], "https://cdn.example.com/starter-logo.png")
        self.assertEqual(
            result["transparent_logo_url"],
            "https://cdn.example.com/starter-logo-transparent.png",
        )
        self.assertEqual(mock_generate_logo.call_args.kwargs["pack_id"], "pack-123")
        self.assertFalse(mock_generate_logo.call_args.kwargs["strict"])


class OnboardingLogoStageTests(unittest.TestCase):
    def test_run_logo_stage_stores_generated_logo_metadata(self) -> None:
        pack_id = uuid4()
        pack = SimpleNamespace(
            id=pack_id,
            name="Acme Pack",
            brand_name="Acme",
            pack_type="enquiries",
            primary_cta=None,
            usp_statement=None,
            usp_proof=None,
            proof_text=None,
            offer_one_liner=None,
            target_audience=None,
            primary_pain=None,
            primary_outcome=None,
            hero_angle=None,
            onboarding_answers={
                "palette": {
                    "primary": "#111111",
                    "secondary": "#222222",
                    "accent": "#333333",
                }
            },
        )
        job = {"stages": onboarding_jobs._default_job_stages()}
        brand_os = SimpleNamespace(
            foundation={
                "one_line_offer": "Launch quickly",
                "brand_industry": "SaaS",
                "main_audience": "Founders",
            }
        )
        stage_calls: list[tuple[str, dict | None]] = []

        def fake_mark_stage(_db, _pack_id, _job_id, _stage_name, status, *, error=None, data=None):
            stage_calls.append((status, data))
            return pack

        with (
            patch.object(onboarding_jobs, "_load_pack_and_job", return_value=(pack, job)),
            patch.object(onboarding_jobs, "_get_existing_onboarding_brand_os", return_value=None),
            patch.object(onboarding_jobs, "_mark_stage", side_effect=fake_mark_stage),
            patch("app.modules.brand_os.services.get_active_for_pack", return_value=brand_os),
            patch(
                "app.modules.brand_os.services.get_summary_fields",
                return_value=("Mission", "Vision", True),
            ),
            patch(
                "app.modules.packs.logo_generation.generate_logo",
                return_value={
                    "logo_url": "https://cdn.example.com/final-logo.png",
                    "wordmark_svg_or_url": "https://cdn.example.com/final-logo-transparent.png",
                    "transparent_logo_url": "https://cdn.example.com/final-logo-transparent.png",
                },
            ),
        ):
            result = onboarding_jobs._run_logo_stage(SimpleNamespace(), pack_id, "job-123")

        self.assertIs(result, pack)
        self.assertEqual(
            pack.onboarding_answers["wordmark_svg_or_url"],
            "https://cdn.example.com/final-logo-transparent.png",
        )
        self.assertEqual(
            pack.onboarding_answers["generated_logo_url"],
            "https://cdn.example.com/final-logo.png",
        )
        self.assertEqual(
            pack.onboarding_answers["transparent_logo_url"],
            "https://cdn.example.com/final-logo-transparent.png",
        )
        self.assertEqual(pack.onboarding_answers["final_logo_job_id"], "job-123")
        self.assertTrue(pack.onboarding_answers["final_logo_completed_at"])
        self.assertEqual(
            json.loads(pack.onboarding_answers["suggested_logos"]),
            [
                "https://cdn.example.com/final-logo.png",
                "https://cdn.example.com/final-logo-transparent.png",
            ],
        )
        self.assertEqual([status for status, _ in stage_calls], ["running", "completed"])
        self.assertEqual(
            stage_calls[-1][1],
            {
                "logo_url": "https://cdn.example.com/final-logo.png",
                "transparent_logo_url": "https://cdn.example.com/final-logo-transparent.png",
            },
        )


if __name__ == "__main__":
    unittest.main()
