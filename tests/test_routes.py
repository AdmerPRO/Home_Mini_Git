"""
Tests for HTML page routes: /, /login, /register, /pagenotfound, and 404 handler.
"""
import pytest


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


class TestRegisterPage:
    def test_register_page_returns_200(self, client):
        res = client.get("/register")
        assert res.status_code == 200

    def test_register_page_returns_html(self, client):
        res = client.get("/register")
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
