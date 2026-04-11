"""Unit tests for app.core.tier_gating module."""

import pytest
from unittest.mock import MagicMock

from app.core.tier_gating import get_user_tier, check_feature, get_project_limit


def _make_user(tier: str | None = None) -> MagicMock:
    user = MagicMock()
    user.tier = tier
    return user


class TestGetUserTier:
    def test_returns_user_tier(self):
        user = _make_user("pro")
        assert get_user_tier(user) == "pro"

    def test_none_tier_defaults_to_free(self):
        user = _make_user(None)
        assert get_user_tier(user) == "free"

    def test_empty_string_defaults_to_free(self):
        user = _make_user("")
        assert get_user_tier(user) == "free"

    def test_invalid_tier_defaults_to_free(self):
        user = _make_user("platinum")
        assert get_user_tier(user) == "free"

    def test_all_valid_tiers(self):
        for tier in ("free", "starter", "pro", "agency"):
            user = _make_user(tier)
            assert get_user_tier(user) == tier

    def test_user_without_tier_attribute_defaults_to_free(self):
        user = MagicMock(spec=[])  # no attributes
        assert get_user_tier(user) == "free"


class TestCheckFeature:
    def test_free_user_cannot_download_logos(self):
        user = _make_user("free")
        assert check_feature(user, "logo_downloads") is False

    def test_starter_user_can_download_logos(self):
        user = _make_user("starter")
        assert check_feature(user, "logo_downloads") is True

    def test_free_user_cannot_export_svg(self):
        user = _make_user("free")
        assert check_feature(user, "svg_export") is False

    def test_free_user_cannot_generate_video(self):
        user = _make_user("free")
        assert check_feature(user, "video_generation") is False

    def test_pro_user_has_video_generation(self):
        user = _make_user("pro")
        assert check_feature(user, "video_generation") is True

    def test_free_has_limited_projects(self):
        user = _make_user("free")
        assert check_feature(user, "max_projects") is True  # int > 0

    def test_unknown_feature_returns_true(self):
        """Features not listed in limits return None, treated as unlimited."""
        user = _make_user("free")
        assert check_feature(user, "nonexistent_feature") is True


class TestGetProjectLimit:
    def test_free_limit_is_1(self):
        user = _make_user("free")
        assert get_project_limit(user) == 1

    def test_starter_limit_is_3(self):
        user = _make_user("starter")
        assert get_project_limit(user) == 3

    def test_agency_limit_is_none(self):
        """Agency tier has unlimited projects (None)."""
        user = _make_user("agency")
        assert get_project_limit(user) is None
