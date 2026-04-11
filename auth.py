import base64
import hashlib
import os
import time

import jwt
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import RedirectResponse, Response

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
SESSION_COOKIE_NAME = "hmg_session"
SESSION_MAX_AGE_SECONDS = 86400
FORCE_SECURE_COOKIE = os.getenv("FORCE_SECURE_COOKIE", "false").lower() == "true"


def _get_fernet() -> Fernet:
    digest = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
    derived_key = base64.urlsafe_b64encode(digest)
    return Fernet(derived_key)


def create_access_token(username: str) -> str:
    now = int(time.time())
    payload = {
        "username": username,
        "iat": now,
        "exp": now + SESSION_MAX_AGE_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str | None:
    try:
        return _get_fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def get_current_username(request: Request) -> str | None:
    encrypted_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not encrypted_token:
        return None

    token = decrypt_token(encrypted_token)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("username")
    return username if isinstance(username, str) and username else None


def _is_secure_request(request: Request) -> bool:
    if FORCE_SECURE_COOKIE:
        return True

    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto.lower() == "https":
        return True

    return request.url.scheme == "https"


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    encrypted_token = encrypt_token(token)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=encrypted_token,
        httponly=True,
        secure=_is_secure_request(request),
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path="/",
    )


def redirect_to_login() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response
