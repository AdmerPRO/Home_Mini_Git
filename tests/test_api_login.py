"""
Tests for POST /api/login
"""
import time
import pytest
import jwt
import os


def _register(client, username="testuser", password="Secret123", now_ms=None):
    """Helper to pre-register a user before login tests."""
    ts = now_ms or int(time.time() * 1000)
    res = client.post("/api/register", json={
        "username": username,
        "password": password,
        "timestamp": ts,
    })
    assert res.status_code == 200, f"Pre-registration failed: {res.json()}"


class TestLoginSuccess:
    def test_login_returns_success_and_token(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "Secret123",
            "timestamp": now_ms,
        })
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "token" in body
        assert isinstance(body["token"], str)
        assert len(body["token"]) > 0

    def test_token_is_valid_jwt(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "Secret123",
            "timestamp": now_ms,
        })
        token = res.json()["token"]
        secret = os.getenv("SECRET_KEY", "supersecretkey123")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["username"] == "testuser"

    def test_token_expires_in_24h(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "Secret123",
            "timestamp": now_ms,
        })
        token = res.json()["token"]
        secret = os.getenv("SECRET_KEY", "supersecretkey123")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        # exp should be ~24h from iat
        delta = payload["exp"] - payload["iat"]
        assert 86390 <= delta <= 86410  # 24h ± 10 s


class TestLoginFailure:
    def test_wrong_password_returns_400(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "WrongPass1",
            "timestamp": now_ms,
        })
        assert res.status_code == 400
        assert "password" in res.json()["detail"].lower()

    def test_nonexistent_user_returns_400(self, client, now_ms):
        res = client.post("/api/login", json={
            "username": "ghost_user",
            "password": "Secret123",
            "timestamp": now_ms,
        })
        assert res.status_code == 400
        assert "not found" in res.json()["detail"].lower()


class TestLoginValidation:
    def test_username_too_short(self, client, now_ms):
        res = client.post("/api/login", json={
            "username": "ab",
            "password": "Secret123",
            "timestamp": now_ms,
        })
        assert res.status_code == 422

    def test_username_invalid_chars(self, client, now_ms):
        res = client.post("/api/login", json={
            "username": "bad user!",
            "password": "Secret123",
            "timestamp": now_ms,
        })
        assert res.status_code == 422

    def test_password_too_short(self, client, now_ms):
        res = client.post("/api/login", json={
            "username": "validuser",
            "password": "abc",
            "timestamp": now_ms,
        })
        assert res.status_code == 422

    def test_password_with_spaces(self, client, now_ms):
        res = client.post("/api/login", json={
            "username": "validuser",
            "password": "pass word",
            "timestamp": now_ms,
        })
        assert res.status_code == 422

    def test_missing_timestamp(self, client):
        res = client.post("/api/login", json={
            "username": "validuser",
            "password": "Secret123",
        })
        assert res.status_code == 422


class TestLoginTimestamp:
    def test_stale_timestamp_returns_400(self, client, now_ms):
        _register(client, now_ms=now_ms)
        old_ts = now_ms - 10_000
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "Secret123",
            "timestamp": old_ts,
        })
        assert res.status_code == 400
        assert "timestamp" in res.json()["detail"].lower()

    def test_future_timestamp_returns_400(self, client, now_ms):
        _register(client, now_ms=now_ms)
        future_ts = now_ms + 10_000
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "Secret123",
            "timestamp": future_ts,
        })
        assert res.status_code == 400

    def test_timestamp_at_edge_of_tolerance(self, client, now_ms):
        _register(client, now_ms=now_ms)
        ts = now_ms - 4_900  # just inside 5 s window
        res = client.post("/api/login", json={
            "username": "testuser",
            "password": "Secret123",
            "timestamp": ts,
        })
        assert res.status_code == 200
