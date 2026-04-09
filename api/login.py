import os
import time

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import User, get_db

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
TIMESTAMP_TOLERANCE_MS = 5000  # max 5 sekund różnicy

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int


@router.post("/login")
@limiter.limit("10/minute")
async def login_user(
    request: Request, req: LoginRequest, db: Session = Depends(get_db)
):
    # Walidacja timestamp — max 5 sekund różnicy od czasu serwera
    server_time_ms = int(time.time() * 1000)
    if abs(server_time_ms - req.timestamp) > TIMESTAMP_TOLERANCE_MS:
        raise HTTPException(status_code=400, detail="Request timestamp out of range")

    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(req.password.encode(), user.password.encode()):
        raise HTTPException(status_code=400, detail="Incorrect password")

    payload = {
        "username": req.username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,  # token ważny 24h
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {"success": True, "token": token}
