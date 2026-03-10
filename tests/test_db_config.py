from __future__ import annotations

import unittest

from app.core.config import Settings


class SettingsDbPoolTests(unittest.TestCase):
    def test_remote_database_enables_pre_ping_in_development(self) -> None:
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url="postgresql://user:pass@db.example.supabase.co:5432/postgres?sslmode=require",
        )

        self.assertTrue(settings.db_pool_pre_ping)

    def test_local_database_keeps_pre_ping_disabled_by_default(self) -> None:
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url="postgresql://postgres:pass@localhost:5432/postgres",
        )

        self.assertFalse(settings.db_pool_pre_ping)

    def test_explicit_pre_ping_override_wins(self) -> None:
        settings = Settings(
            _env_file=None,
            app_env="development",
            database_url="postgresql://user:pass@db.example.supabase.co:5432/postgres?sslmode=require",
            db_pool_pre_ping=False,
        )

        self.assertFalse(settings.db_pool_pre_ping)


if __name__ == "__main__":
    unittest.main()
