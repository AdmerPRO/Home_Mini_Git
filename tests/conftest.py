"""
Shared pytest fixtures for Home_Mini_Git-server tests.
"""

import os
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use in-memory SQLite for tests — never touches the real Database.db
# StaticPool ensures all connections share the same in-memory database
TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    # Import Base after engine is ready so metadata is available
    from core.database import Base

    Base.metadata.create_all(bind=test_engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    import app_paths as app_paths_wrapper
    from core import app_paths as core_app_paths

    monkeypatch.setattr(core_app_paths, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(app_paths_wrapper, "DATA_ROOT", tmp_path)
    return tmp_path


@pytest.fixture()
def db_session(test_session_factory, test_engine):
    """Fresh DB session per test; cleans all tables after each test."""
    from core.database import Base

    # Safety net: ensure tables exist on the test engine regardless of
    # import order (e.g. if main.py was imported before this fixture ran).
    Base.metadata.create_all(bind=test_engine)

    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Delete all rows from every table so each test starts with a clean DB
        with test_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


@pytest.fixture()
def client(db_session, data_root):
    """
    TestClient with the real FastAPI app, but with the DB dependency
    overridden to use the in-memory test database.
    """
    from core.database import get_db
    from core.rate_limit import limiter
    from core.security import reset_login_protection_state
    from main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    limiter.enabled = False
    reset_login_protection_state()
    app.state.limiter = limiter

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
    reset_login_protection_state()
    limiter.enabled = True


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
