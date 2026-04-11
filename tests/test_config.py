"""Unit tests for app.core.config module."""

import pytest
from app.core.config import _database_uses_remote_host


class TestDatabaseUsesRemoteHost:
    def test_empty_string_is_not_remote(self):
        assert _database_uses_remote_host("") is False

    def test_localhost_is_not_remote(self):
        assert _database_uses_remote_host("postgresql://localhost:5432/db") is False

    def test_127_0_0_1_is_not_remote(self):
        assert _database_uses_remote_host("postgresql://127.0.0.1:5432/db") is False

    def test_ipv6_loopback_is_not_remote(self):
        assert _database_uses_remote_host("postgresql://[::1]:5432/db") is False

    def test_sqlite_is_not_remote(self):
        assert _database_uses_remote_host("sqlite:///./test.db") is False

    def test_remote_host_is_remote(self):
        assert _database_uses_remote_host("postgresql://db.supabase.co:5432/mydb") is True

    def test_async_driver_remote(self):
        assert _database_uses_remote_host("postgresql+asyncpg://prod.example.com/db") is True

    def test_invalid_url_returns_false(self):
        # Malformed URL should not crash
        assert _database_uses_remote_host("not-a-url") is False

    def test_no_host_is_not_remote(self):
        assert _database_uses_remote_host("postgresql:///mydb") is False
