"""
Tests for POST /api/register
"""

import time


class TestRegisterSuccess:
    def test_register_returns_success(self, client, valid_register_payload):
        res = client.post("/api/register", json=valid_register_payload)
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "testuser" in body["message"]

    def test_register_password_is_hashed_in_db(
        self, client, db_session, valid_register_payload
    ):
        client.post("/api/register", json=valid_register_payload)
        from core.database import User

        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user is not None
        assert user.password != "Secret123"
        assert user.password.startswith("$2b$")

    def test_register_stores_correct_username(
        self, client, db_session, valid_register_payload
    ):
        client.post("/api/register", json=valid_register_payload)
        from core.database import User

        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user.username == "testuser"

    def test_register_stores_timestamp(
        self, client, db_session, valid_register_payload
    ):
        client.post("/api/register", json=valid_register_payload)
        from core.database import User

        user = db_session.query(User).filter(User.username == "testuser").first()
        now_ms = int(time.time() * 1000)
        assert now_ms - 5_000 <= user.created_at <= now_ms


class TestRegisterDuplicate:
    def test_duplicate_username_returns_400(self, client, valid_register_payload):
        client.post("/api/register", json=valid_register_payload)
        res = client.post("/api/register", json=valid_register_payload)
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"]


class TestRegisterValidation:
    def test_username_too_short(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "ab",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_username_too_long(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "a" * 51,
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_username_invalid_characters(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "user name!",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_password_too_short(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "abc",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_password_too_long(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "x" * 129,
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_password_with_whitespace(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "pass word",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_missing_timestamp_is_accepted(self, client):
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "Secret123",
            },
        )
        assert res.status_code == 200

    def test_missing_username(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422

    def test_missing_password(self, client, now_ms):
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "timestamp": now_ms,
            },
        )
        assert res.status_code == 422


class TestRegisterProtection:
    def test_rate_limit_is_disabled_in_tests(self, client, now_ms):
        for index in range(6):
            res = client.post(
                "/api/register",
                json={
                    "username": f"validuser_{index}",
                    "password": "Secret123",
                    "timestamp": now_ms,
                },
            )
            assert res.status_code == 200

    def test_old_timestamp_is_ignored(self, client):
        old_ts = int(time.time() * 1000) - 10_000  # 10 seconds ago
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "Secret123",
                "timestamp": old_ts,
            },
        )
        assert res.status_code == 200

    def test_future_timestamp_is_ignored(self, client):
        future_ts = int(time.time() * 1000) + 10_000  # 10 seconds in future
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "Secret123",
                "timestamp": future_ts,
            },
        )
        assert res.status_code == 200

    def test_current_timestamp_is_ignored(self, client, now_ms):
        # 3 seconds ago — within 5 s tolerance
        ts = now_ms - 3_000
        res = client.post(
            "/api/register",
            json={
                "username": "validuser",
                "password": "Secret123",
                "timestamp": ts,
            },
        )
        assert res.status_code == 200
