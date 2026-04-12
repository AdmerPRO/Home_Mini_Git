"""
Tests for HTML page routes: /, /login, /register, /pagenotfound, and 404 handler.
"""

from core.auth import SESSION_COOKIE_NAME


class TestRootPage:
    def test_root_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_root_returns_html(self, client):
        res = client.get("/")
        assert "text/html" in res.headers["content-type"]

    def test_root_has_body_content(self, client):
        res = client.get("/")
        assert len(res.text) > 0


class TestLoginPage:
    def test_login_page_returns_200(self, client):
        res = client.get("/login")
        assert res.status_code == 200

    def test_login_page_returns_html(self, client):
        res = client.get("/login")
        assert "text/html" in res.headers["content-type"]


class TestDashboardPage:
    def test_dashboard_redirects_to_login_without_session(self, client):
        res = client.get("/dashboard", follow_redirects=False)
        assert res.status_code == 303
        assert res.headers["location"] == "/login"
        assert SESSION_COOKIE_NAME in res.headers.get("set-cookie", "")

    def test_dashboard_returns_200_for_authenticated_user(self, client, now_ms):
        client.post(
            "/api/register",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )
        client.post(
            "/api/login",
            json={
                "username": "testuser",
                "password": "Secret123",
                "timestamp": now_ms,
            },
        )

        res = client.get("/dashboard")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert res.headers["Cache-Control"] == "no-store"
        assert "Hey!" in res.text


class TestRegisterPage:
    def test_register_page_returns_200(self, client):
        res = client.get("/register")
        assert res.status_code == 200

    def test_register_page_returns_html(self, client):
        res = client.get("/register")
        assert "text/html" in res.headers["content-type"]


class TestExplorePage:
    def test_explore_page_returns_200(self, client):
        res = client.get("/explore")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]


class TestPublicDetailPages:
    def test_user_profile_page_returns_200(self, client):
        res = client.get("/users/testuser")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]

    def test_repository_page_returns_200(self, client):
        res = client.get("/repositories/testuser/example")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]


class TestPageNotFound:
    def test_pagenotfound_route_returns_200(self, client):
        res = client.get("/pagenotfound")
        assert res.status_code == 200

    def test_pagenotfound_returns_html(self, client):
        res = client.get("/pagenotfound")
        assert "text/html" in res.headers["content-type"]


class TestGlobal404Handler:
    def test_unknown_route_returns_404(self, client):
        res = client.get("/this-does-not-exist")
        assert res.status_code == 404

    def test_unknown_route_returns_html_not_json(self, client):
        res = client.get("/nonexistent-page")
        assert "text/html" in res.headers["content-type"]

    def test_unknown_api_route_returns_404(self, client):
        res = client.get("/api/nonexistent")
        assert res.status_code == 404


class TestSecurityHeaders:
    def test_root_response_contains_security_headers(self, client):
        res = client.get("/")

        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert res.headers["Referrer-Policy"] == "no-referrer"
        assert "default-src 'self'" in res.headers["Content-Security-Policy"]

    def test_session_response_disables_caching(self, client):
        res = client.get("/api/session")
        assert res.headers["Cache-Control"] == "no-store"
