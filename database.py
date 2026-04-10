from typing import Generator

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite:///./Database.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)  # only the hash is stored here
    created_at = Column(Integer, nullable=False)


# NOTE: Base.metadata.create_all() is intentionally NOT called here.
# Production tables are created by the @app.on_event("startup") hook in main.py.
# Test tables are created by the test_session_factory fixture in tests/conftest.py.
# Calling create_all() at import time would always hit the production engine,
# even when the test suite overrides the DB dependency.


# Shared dependency — used by api/login.py and api/register.py
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["engine", "SessionLocal", "Base", "User", "get_db"]
