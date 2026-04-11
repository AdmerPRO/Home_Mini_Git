"""
Tests for auth session helpers.
"""

from fastapi import Request
from fastapi.responses import Response

from auth import (SESSION_COOKIE_NAME, clear_session_cookie,
                  create_access_token, decode_access_token, decrypt_token,
                  encrypt_token, get_current_username, set_session_cookie)


def _build_request(cookies=None, scheme="http", headers=None):
    cookie_header = ""
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())

    raw_headers = []
    if cookie_header:
        raw_headers.append((b"cookie", cookie_header.encode("utf-8")))

    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
        "scheme": scheme,
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }
    return Request(scope)


class TestTokenHelpers:
    def test_encrypt_and_decrypt_token_roundtrip(self):
        token = create_access_token("roundtrip_user")
        encrypted = encrypt_token(token)

        assert encrypted != token
        assert decrypt_token(encrypted) == token

    def test_decode_access_token_returns_payload(self):
        token = create_access_token("decoded_user")
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["username"] == "decoded_user"

    def test_decrypt_token_returns_none_for_invalid_value(self):
        assert decrypt_token("not-a-valid-encrypted-token") is None


class TestCookieHelpers:
    def test_get_current_username_returns_none_without_cookie(self):
        request = _build_request()
        assert get_current_username(request) is None

    def test_get_current_username_returns_none_for_tampered_cookie(self):
        request = _build_request(cookies={SESSION_COOKIE_NAME: "tampered-cookie"})
        assert get_current_username(request) is None

    def test_get_current_username_returns_username_for_valid_cookie(self):
        token = create_access_token("cookie_user")
        encrypted = encrypt_token(token)
        request = _build_request(cookies={SESSION_COOKIE_NAME: encrypted})

        assert get_current_username(request) == "cookie_user"

    def test_set_session_cookie_uses_secure_flag_for_https(self):
        request = _build_request(scheme="https")
        response = Response()
        token = create_access_token("secure_user")

        set_session_cookie(response, request, token)
        cookie_header = response.headers.get("set-cookie", "")

        assert SESSION_COOKIE_NAME in cookie_header
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header
        assert "Secure" in cookie_header

    def test_set_session_cookie_uses_secure_flag_for_forwarded_https(self):
        request = _build_request(headers={"x-forwarded-proto": "https"})
        response = Response()
        token = create_access_token("proxy_user")

        set_session_cookie(response, request, token)
        cookie_header = response.headers.get("set-cookie", "")

        assert "Secure" in cookie_header

    def test_clear_session_cookie_expires_cookie(self):
        response = Response()
        clear_session_cookie(response)
        cookie_header = response.headers.get("set-cookie", "")

        assert SESSION_COOKIE_NAME in cookie_header
        assert "Max-Age=0" in cookie_header
