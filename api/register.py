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
from core.rate_limit import limiter
from core.security import hash_identifier
from utils.repository_manager_util import add_user, setup_start

load_dotenv()
SALT_ROUNDS = int(os.getenv("BCRYPT_SALT_ROUNDS", 12))

router = APIRouter()
logger = get_logger(__name__)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")


@router.post("/register")
@limiter.limit("5/minute")
async def register_user(
    request: Request, req: RegisterRequest, db: Session = Depends(get_db)
):
    client_host = request.client.host if request.client else "unknown"
    user_hash = hash_identifier(req.username)
    logger.info(
        "Registration attempt for user_hash=%s from ip=%s", user_hash, client_host
    )

    # Validate timestamp — max 5 seconds difference from server time
    if db.query(User).filter(User.username == req.username).first():
        logger.warning("Rejected registration for existing user_hash=%s", user_hash)
        raise HTTPException(status_code=400, detail="User already exists")

    logger.debug("Registration payload validated for user_hash=%s", user_hash)

    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    hashed_pw = bcrypt.hashpw(req.password.encode(), salt).decode()
    logger.debug("Password hashed for user_hash=%s", user_hash)

    created_at = int(time.time() * 1000)
    user = User(username=req.username, password=hashed_pw, created_at=created_at)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.debug("User saved in database for user_hash=%s", user_hash)

    setup_start(app_paths.DATA_ROOT)
    add_user(app_paths.DATA_ROOT, req.username, joined_at=created_at)
    logger.info("User registered successfully user_hash=%s", user_hash)

    return {"success": True, "message": f"User {req.username} registered"}
