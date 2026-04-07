from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import SessionLocal, User
import bcrypt
import jwt
import time
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")

router = APIRouter()

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
async def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not bcrypt.checkpw(req.password.encode(), user.password.encode()):
        raise HTTPException(status_code=400, detail="Incorrect password")

    payload = {
        "username": req.username,
        "iat": int(time.time() * 1000),
        "timestamp": req.timestamp
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {"success": True, "token": token}