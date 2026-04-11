"""
Tests for POST /api/login
"""

import os
import time

import jwt

from auth import SESSION_COOKIE_NAME
from utils.file_manager_util import create_project


def _register(client, username="testuser", password="Secret123", now_ms=None):
    """Helper to pre-register a user before login tests."""
    ts = now_ms or int(time.time() * 1000)
    res = client.post(
        "/api/register",
        json={
            "username": username,
            "password": password,
            "timestamp": ts,
        },
    )
    assert res.status_code == 200, f"Pre-registration failed: {res.json()}"


class TestLoginSuccess:
    def test_login_returns_success_and_token(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "token" in body
        assert isinstance(body["token"], str)
        assert len(body["token"]) > 0
        assert body["nickname"] == "testuser"

    def test_login_sets_encrypted_session_cookie(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )

        cookie_header = res.headers.get("set-cookie", "")
        assert SESSION_COOKIE_NAME in cookie_header
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header
        assert res.cookies.get(SESSION_COOKIE_NAME)

    def test_token_is_valid_jwt(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        token = res.json()["token"]
        secret = os.getenv("SECRET_KEY", "supersecretkey123")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["username"] == "testuser"

    def test_token_expires_in_24h(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        token = res.json()["token"]
        secret = os.getenv("SECRET_KEY", "supersecretkey123")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        # exp should be ~24h from iat
        delta = payload["exp"] - payload["iat"]
        assert 86390 <= delta <= 86410  # 24h ± 10 s


class TestLoginFailure:
    def test_wrong_password_returns_400(self, client, now_ms):
        _register(client, now_ms=now_ms)
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "WrongPass1",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 400
        assert "password" in res.json()["detail"].lower()

    def test_nonexistent_user_returns_400(self, client, now_ms):
        res = client.post(
            "/api/login",
            json={
                "username": "ghost_user",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 400
        assert "not found" in res.json()["detail"].lower()


class TestLoginValidation:
    def test_username_too_short(self, client, now_ms):
        res = client.post(
            "/api/login",
            json={
                "username": "ab",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_username_invalid_chars(self, client, now_ms):
        res = client.post(
            "/api/login",
            json={
                "username": "bad user!",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_password_too_short(self, client, now_ms):
        res = client.post(
            "/api/login",
            json={
                "username": "validuser",
                "password": "abc",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_password_with_spaces(self, client, now_ms):
        res = client.post(
            "/api/login",
            json={
                "username": "validuser",
                "password": "pass word",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_missing_timestamp(self, client):
        res = client.post(
            "/api/login",
            json={
                "username": "validuser",
                "password": "Secret123",
            },
        )
        assert res.status_code == 422


class TestLoginTimestamp:
    def test_stale_timestamp_returns_400(self, client, now_ms):
        _register(client, now_ms=now_ms)
        old_ts = now_ms - 10_000
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": old_ts,
            },
        )
        assert res.status_code == 400
        assert "timestamp" in res.json()["detail"].lower()

    def test_future_timestamp_returns_400(self, client, now_ms):
        _register(client, now_ms=now_ms)
        future_ts = now_ms + 10_000
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": future_ts,
            },
        )
        assert res.status_code == 400

    def test_timestamp_at_edge_of_tolerance(self, client, now_ms):
        _register(client, now_ms=now_ms)
        ts = now_ms - 4_900  # just inside 5 s window
        res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": ts,
            },
        )
        assert res.status_code == 200


class TestSessionFlow:
    def test_session_returns_authenticated_user_and_projects(self, client, now_ms):
        _register(client, now_ms=now_ms)
        login_res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )

        client.cookies.set(
            SESSION_COOKIE_NAME, login_res.cookies.get(SESSION_COOKIE_NAME)
        )
        session_res = client.get("/api/session")
        body = session_res.json()

        assert session_res.status_code == 200
        assert body["authenticated"] is True
        assert body["nickname"] == "testuser"
        assert body["projects"] == []

    def test_session_returns_projects_for_authenticated_user(
        self, client, now_ms, tmp_path
    ):
        _register(client, now_ms=now_ms)
        login_res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )

        create_project(tmp_path, "testuser", "alpha", private=True)
        create_project(tmp_path, "testuser", "beta", private=False)

        from api import session as session_module

        original_get_user_projects = session_module.get_user_projects
        session_module.get_user_projects = (
            lambda _base, username: original_get_user_projects(tmp_path, username)
        )
        try:
            client.cookies.set(
                SESSION_COOKIE_NAME, login_res.cookies.get(SESSION_COOKIE_NAME)
            )
            session_res = client.get("/api/session")
        finally:
            session_module.get_user_projects = original_get_user_projects

        body = session_res.json()
        assert session_res.status_code == 200
        assert body["authenticated"] is True
        assert body["projects"] == ["alpha", "beta"]

    def test_session_returns_unauthenticated_without_cookie(self, client):
        session_res = client.get("/api/session")

        assert session_res.status_code == 200
        assert session_res.json() == {"authenticated": False}

    def test_session_returns_unauthenticated_for_invalid_cookie(self, client):
        client.cookies.set(SESSION_COOKIE_NAME, "broken-cookie")
        session_res = client.get("/api/session")

        assert session_res.status_code == 200
        assert session_res.json() == {"authenticated": False}

    def test_session_returns_unauthenticated_when_user_was_removed(
        self, client, now_ms, db_session
    ):
        _register(client, now_ms=now_ms)
        login_res = client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )

        from database import User

        user = db_session.query(User).filter(User.username == "testuser").first()
        db_session.delete(user)
        db_session.commit()

        client.cookies.set(
            SESSION_COOKIE_NAME, login_res.cookies.get(SESSION_COOKIE_NAME)
        )
        session_res = client.get("/api/session")

        assert session_res.status_code == 200
        assert session_res.json() == {"authenticated": False}
        assert SESSION_COOKIE_NAME in session_res.headers.get("set-cookie", "")

    def test_logout_clears_session_cookie(self, client, now_ms):
        _register(client, now_ms=now_ms)
        client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )

        logout_res = client.post("/api/logout")

        assert logout_res.status_code == 200
        assert SESSION_COOKIE_NAME in logout_res.headers.get("set-cookie", "")
        assert "Max-Age=0" in logout_res.headers.get("set-cookie", "")
        assert logout_res.json() == {"success": True}
