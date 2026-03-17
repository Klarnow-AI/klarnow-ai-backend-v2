from __future__ import annotations

import os
import unittest

from app.core.config import Settings

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-db-config.db")

from app.core.db import session as session_module


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

    def test_sqlite_engine_kwargs_use_sqlite_timeout_key(self) -> None:
        settings = Settings(
            _env_file=None,
            database_url="sqlite:///./test-db-config-timeout.db",
            db_connect_timeout_seconds=7,
        )

        self.assertEqual(
            session_module._build_engine_kwargs(settings)["connect_args"],
            {"timeout": 7},
        )

    def test_postgres_engine_kwargs_use_connect_timeout_key(self) -> None:
        settings = Settings(
            _env_file=None,
            database_url="postgresql://user:pass@localhost:5432/postgres",
            db_connect_timeout_seconds=7,
        )

        self.assertEqual(
            session_module._build_engine_kwargs(settings)["connect_args"],
            {"connect_timeout": 7},
        )


if __name__ == "__main__":
    unittest.main()
