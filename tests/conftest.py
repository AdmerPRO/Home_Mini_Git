"""
Shared pytest fixtures for Home_Mini_Git-server tests.
"""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests — never touches the real Database.db
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    return engine


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    # Import Base after engine is ready so metadata is available
    from database import Base

    Base.metadata.create_all(bind=test_engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def db_session(test_session_factory):
    """Fresh DB session per test; rolls back after each test."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db_session):
    """
    TestClient with the real FastAPI app, but with the DB dependency
    overridden to use the in-memory test database.
    """
    from database import get_db
    from main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def now_ms() -> int:
    """Current Unix timestamp in milliseconds."""
    return int(time.time() * 1000)


@pytest.fixture()
def valid_register_payload(now_ms):
    return {
        "username": "testuser",
        "password": "Secret123",
        "timestamp": now_ms,
    }


@pytest.fixture()
def valid_login_payload(now_ms):
    return {
        "username": "testuser",
        "password": "Secret123",
        "timestamp": now_ms,
    }
