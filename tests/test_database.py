"""
Tests for database.py — User model, get_db dependency, schema.
"""
import time
import pytest
import bcrypt
from sqlalchemy import inspect


class TestUserModel:
    def test_user_table_exists(self, test_engine):
        inspector = inspect(test_engine)
        assert "users" in inspector.get_table_names()

    def test_user_columns_exist(self, test_engine):
        inspector = inspect(test_engine)
        cols = {c["name"] for c in inspector.get_columns("users")}
        assert {"username", "password", "created_at"} <= cols

    def test_create_user(self, db_session):
        from database import User
        hashed = bcrypt.hashpw(b"Secret123", bcrypt.gensalt()).decode()
        user = User(
            username="dbtest",
            password=hashed,
            created_at=int(time.time() * 1000),
        )
        db_session.add(user)
        db_session.commit()

        fetched = db_session.query(User).filter(User.username == "dbtest").first()
        assert fetched is not None
        assert fetched.username == "dbtest"

    def test_username_is_primary_key(self, test_engine):
        inspector = inspect(test_engine)
        pk = inspector.get_pk_constraint("users")
        assert "username" in pk["constrained_columns"]

    def test_password_column_not_nullable(self, test_engine):
        inspector = inspect(test_engine)
        cols = {c["name"]: c for c in inspector.get_columns("users")}
        assert cols["password"]["nullable"] is False

    def test_duplicate_username_raises(self, db_session):
        from database import User
        from sqlalchemy.exc import IntegrityError
        ts = int(time.time() * 1000)
        hashed = bcrypt.hashpw(b"Secret123", bcrypt.gensalt()).decode()
        db_session.add(User(username="dup", password=hashed, created_at=ts))
        db_session.commit()

        db_session.add(User(username="dup", password=hashed, created_at=ts))
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestGetDb:
    def test_get_db_yields_session(self):
        from database import get_db
        gen = get_db()
        session = next(gen)
        assert session is not None
        # Exhaust generator (triggers finally block)
        try:
            next(gen)
        except StopIteration:
            pass
