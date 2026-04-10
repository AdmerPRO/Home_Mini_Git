import os
import time

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import User, get_db

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
TIMESTAMP_TOLERANCE_MS = 5200  # 5 s tolerance + ~200 ms buffer for processing delay

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int


@router.post("/login")
async def login_user(
    request: Request, req: LoginRequest, db: Session = Depends(get_db)
):
    # Validate timestamp — max 5 seconds difference from server time
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
        "exp": int(time.time()) + 86400,  # token valid for 24h
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {"success": True, "token": token}
