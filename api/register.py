import os
import time

import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import app_paths
from core.database import User, get_db
from core.logger import get_logger
from utils.repository_manager_util import add_user, setup_start

load_dotenv()
SALT_ROUNDS = int(os.getenv("BCRYPT_SALT_ROUNDS", 12))
TIMESTAMP_TOLERANCE_MS = 5000  # max 5 seconds difference

router = APIRouter()
logger = get_logger(__name__)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int


@router.post("/register")
async def register_user(
    request: Request, req: RegisterRequest, db: Session = Depends(get_db)
):
    client_host = request.client.host if request.client else "unknown"
    logger.info(
        "Registration attempt for user=%s from ip=%s", req.username, client_host
    )

    # Validate timestamp — max 5 seconds difference from server time
    server_time_ms = int(time.time() * 1000)
    if abs(server_time_ms - req.timestamp) > TIMESTAMP_TOLERANCE_MS:
        logger.warning(
            "Rejected registration for user=%s due to invalid timestamp", req.username
        )
        raise HTTPException(status_code=400, detail="Request timestamp out of range")

    if db.query(User).filter(User.username == req.username).first():
        logger.warning("Rejected registration for existing user=%s", req.username)
        raise HTTPException(status_code=400, detail="User already exists")

    logger.debug("Registration payload validated for user=%s", req.username)

    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    hashed_pw = bcrypt.hashpw(req.password.encode(), salt).decode()
    logger.debug("Password hashed for user=%s", req.username)

    user = User(username=req.username, password=hashed_pw, created_at=req.timestamp)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.debug("User saved in database for user=%s", user.username)

    setup_start(app_paths.DATA_ROOT)
    add_user(app_paths.DATA_ROOT, req.username, joined_at=req.timestamp)
    logger.info("User registered successfully user=%s", req.username)

    return {"success": True, "message": f"User {req.username} registered"}
