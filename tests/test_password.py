"""Unit tests for password hashing (bcrypt).

Tests bcrypt directly to avoid deep import chain that requires psycopg2.
"""

import pytest
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


class TestHashPassword:
    def test_returns_string(self):
        result = hash_password("mysecret")
        assert isinstance(result, str)

    def test_hash_differs_from_plaintext(self):
        result = hash_password("mysecret")
        assert result != "mysecret"

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # bcrypt salts are random

    def test_hash_starts_with_bcrypt_prefix(self):
        result = hash_password("test")
        assert result.startswith("$2b$") or result.startswith("$2a$")


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = hash_password("correct_pass")
        assert verify_password("correct_pass", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password("correct_pass")
        assert verify_password("wrong_pass", hashed) is False

    def test_empty_password_can_be_hashed_and_verified(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_unicode_password(self):
        pw = "p@ssw0rd_with_unicod3_\u00e9\u00e8\u00ea"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_long_password(self):
        pw = "a" * 100
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True
