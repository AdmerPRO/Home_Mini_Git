import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import create_access_token, set_session_cookie
from core.database import User, get_db
from core.logger import get_logger
from core.rate_limit import limiter
from core.security import (
    clear_failed_logins,
    hash_identifier,
    is_account_locked,
    register_failed_login,
)

router = APIRouter()
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=10, max_length=128, pattern=r"^\S+$")


@router.post("/login")
@limiter.limit("5/minute")
async def login_user(
    request: Request,
    req: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    client_host = request.client.host if request.client else "unknown"
    user_hash = hash_identifier(req.username)
    logger.info("Login attempt for user_hash=%s from ip=%s", user_hash, client_host)

    # Validate timestamp — max 5 seconds difference from server time
    if is_account_locked(req.username, ip=client_host):
        logger.warning(
            "Rejected login for locked account user_hash=%s from ip=%s",
            user_hash,
            client_host,
        )
        raise HTTPException(
            status_code=429, detail="Too many login attempts. Try again later."
        )

    user = db.query(User).filter(User.username == req.username).first()
    valid_credentials = bool(user) and bcrypt.checkpw(
        req.password.encode(), user.password.encode()
    )
    if not valid_credentials:
        locked = register_failed_login(req.username, ip=client_host)
        logger.warning(
            "Rejected login due to invalid credentials for user_hash=%s from ip=%s",
            user_hash,
            client_host,
        )
        if locked:
            raise HTTPException(
                status_code=429, detail="Too many login attempts. Try again later."
            )
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(req.username)
    set_session_cookie(response, request, token)
    response.headers["Cache-Control"] = "no-store"
    clear_failed_logins(req.username, ip=client_host)
    logger.debug("Session cookie set for user_hash=%s", user_hash)
    logger.info("User logged in successfully user_hash=%s", user_hash)

    return {"success": True, "nickname": req.username}
