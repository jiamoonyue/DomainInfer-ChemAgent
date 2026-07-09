"""Tests for security utilities."""

import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecret123")
        assert verify_password("mysecret123", hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "user-123", "role": "user"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_invalid_token(self):
        payload = decode_token("not.a.valid.token")
        assert payload is None

    def test_empty_token(self):
        payload = decode_token("")
        assert payload is None
