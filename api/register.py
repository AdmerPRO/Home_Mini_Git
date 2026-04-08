from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db, User
import bcrypt
import time
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
import os

load_dotenv()
SALT_ROUNDS = int(os.getenv("BCRYPT_SALT_ROUNDS", 12))
TIMESTAMP_TOLERANCE_MS = 5000  # max 5 sekund różnicy

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int

@router.post("/register")
@limiter.limit("5/minute")
async def register_user(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    # Walidacja timestamp — max 5 sekund różnicy od czasu serwera
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
