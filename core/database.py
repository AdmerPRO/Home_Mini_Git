import os
from pathlib import Path
from typing import Generator

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core import app_paths

DEFAULT_DATABASE_DIR = app_paths.SERVER_ROOT / "data"
DEFAULT_DATABASE_PATH = DEFAULT_DATABASE_DIR / "Database.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}")

if DATABASE_URL == f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}":
    DEFAULT_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(DEFAULT_DATABASE_DIR, 0o700)
    except OSError:
        pass

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)  # only the hash is stored here
    created_at = Column(Integer, nullable=False)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti = Column(String, primary_key=True)
    exp = Column(Integer, nullable=False, index=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

__all__ = ["engine", "SessionLocal", "Base", "User", "RevokedToken", "get_db"]
