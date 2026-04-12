import time

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import create_access_token, set_session_cookie
from database import User, get_db
from logger import get_logger

TIMESTAMP_TOLERANCE_MS = 5500  # 5 s tolerance + ~500 ms buffer for processing delay

router = APIRouter()
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int


@router.post("/login")
async def login_user(
    request: Request,
    req: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    client_host = request.client.host if request.client else "unknown"
    logger.info("Login attempt for user=%s from ip=%s", req.username, client_host)

    # Validate timestamp — max 5 seconds difference from server time
    server_time_ms = int(time.time() * 1000)
    if abs(server_time_ms - req.timestamp) > TIMESTAMP_TOLERANCE_MS:
        logger.warning(
            "Rejected login for user=%s due to invalid timestamp", req.username
        )
        raise HTTPException(status_code=400, detail="Request timestamp out of range")

    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        logger.warning("Rejected login because user=%s was not found", req.username)
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(req.password.encode(), user.password.encode()):
        logger.warning(
            "Rejected login due to invalid password for user=%s", req.username
        )
        raise HTTPException(status_code=400, detail="Incorrect password")

    token = create_access_token(req.username)
    set_session_cookie(response, request, token)
    response.headers["Cache-Control"] = "no-store"
    logger.debug("Session cookie set for user=%s", req.username)
    logger.info("User logged in successfully user=%s", req.username)

    return {"success": True, "token": token, "nickname": req.username}
