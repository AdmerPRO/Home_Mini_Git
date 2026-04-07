from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import SessionLocal, User
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()
SALT_ROUNDS = int(os.getenv("BCRYPT_SALT_ROUNDS", 12))

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128, pattern=r"^\S+$")
    timestamp: int  # w ms

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
async def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    hashed_pw = bcrypt.hashpw(req.password.encode(), salt).decode()

    user = User(username=req.username, password=hashed_pw, created_at=req.timestamp)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"success": True, "message": f"User {req.username} registered"}