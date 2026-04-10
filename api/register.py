import os
import time

import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import User, get_db

load_dotenv()
SALT_ROUNDS = int(os.getenv("BCRYPT_SALT_ROUNDS", 12))
TIMESTAMP_TOLERANCE_MS = 5000  # max 5 seconds difference

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int


@router.post("/register")
async def register_user(
    request: Request, req: RegisterRequest, db: Session = Depends(get_db)
):
    # Validate timestamp — max 5 seconds difference from server time
    server_time_ms = int(time.time() * 1000)
    if abs(server_time_ms - req.timestamp) > TIMESTAMP_TOLERANCE_MS:
        raise HTTPException(status_code=400, detail="Request timestamp out of range")

    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    hashed_pw = bcrypt.hashpw(req.password.encode(), salt).decode()

    user = User(username=req.username, password=hashed_pw, created_at=req.timestamp)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"success": True, "message": f"User {req.username} registered"}
