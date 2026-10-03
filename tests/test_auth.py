"""
test_auth.py — Unit & Integration Tests for User Authentication
===============================================================
Tests cover:
- Database schema initialization
- Password hashing & verification
- Email validation & duplicate registration handling
- Auth API endpoints (/api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/me)
- Session creation, validation, and destruction
- Sanitization (verifying password hashes are never exposed)
"""

from __future__ import annotations

import sqlite3
import pytest

from api import app
from database import init_db, get_db_connection
from services.auth_service import (
    register_user,
    authenticate_user,
    get_user_by_id,
    validate_email,
    validate_password,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Use an isolated temporary SQLite database for tests."""
    db_file = str(tmp_path / "test_auth.db")
    monkeypatch.setattr("config.settings.DATABASE_PATH", db_file)
    init_db()
    yield db_file


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestValidation:
    def test_email_validation(self):
        assert validate_email("user@example.com") is True
        assert validate_email("user.name+tag@sub.domain.co.in") is True
        assert validate_email("invalid-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("") is False

    def test_password_validation(self):
        valid, msg = validate_password("secret123")
        assert valid is True
        assert msg == ""

        short_valid, short_msg = validate_password("12345")
        assert short_valid is False
        assert "at least 6 characters" in short_msg


class TestAuthService:
    def test_register_user_success(self):
        user, err = register_user("Ananya Sen", "ananya@example.com", "password123")
        assert err == ""
        assert user is not None
        assert user["full_name"] == "Ananya Sen"
        assert user["email"] == "ananya@example.com"
        assert "password_hash" not in user

    def test_register_duplicate_email_fails(self):
        user1, err1 = register_user("User One", "dup@example.com", "password123")
        assert err1 == ""
        assert user1 is not None

        user2, err2 = register_user("User Two", "dup@example.com", "password456")
        assert user2 is None
        assert "already exists" in err2

    def test_register_invalid_email_fails(self):
        user, err = register_user("Bad Email", "notanemail", "password123")
        assert user is None
        assert "Invalid email address format" in err

    def test_register_empty_name_fails(self):
        user, err = register_user("   ", "valid@example.com", "password123")
        assert user is None
        assert "Full name is required" in err

    def test_authenticate_user_success(self):
        register_user("Vijay Kumar", "vijay@example.com", "mysecretpw")
        user, err = authenticate_user("vijay@example.com", "mysecretpw")
        assert err == ""
        assert user is not None
        assert user["email"] == "vijay@example.com"

    def test_authenticate_user_incorrect_password(self):
        register_user("Vijay Kumar", "vijay@example.com", "mysecretpw")
        user, err = authenticate_user("vijay@example.com", "wrongpassword")
        assert user is None
        assert "Invalid email or password" in err

    def test_authenticate_user_nonexistent_email(self):
        user, err = authenticate_user("nobody@example.com", "somepassword")
        assert user is None
        assert "Invalid email or password" in err

    def test_password_hash_stored_in_database(self):
        register_user("Hash Test", "hash@example.com", "secret567")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE email = 'hash@example.com'")
            row = cursor.fetchone()
            assert row is not None
            raw_hash = row["password_hash"]
            assert raw_hash != "secret567"
            assert raw_hash.startswith("scrypt:") or len(raw_hash) > 20


class TestAuthEndpoints:
    def test_api_register_endpoint(self, client):
        res = client.post("/api/auth/register", json={
            "full_name": "Priya Sharma",
            "email": "priya@example.com",
            "password": "securepassword123"
        })
        assert res.status_code == 201
        data = res.get_json()
        assert "user" in data
        assert data["user"]["email"] == "priya@example.com"
        assert "password_hash" not in data["user"]

    def test_api_login_endpoint(self, client):
        client.post("/api/auth/register", json={
            "full_name": "Priya Sharma",
            "email": "priya@example.com",
            "password": "securepassword123"
        })
        res = client.post("/api/auth/login", json={
            "email": "priya@example.com",
            "password": "securepassword123"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["user"]["email"] == "priya@example.com"

        # Check /api/auth/me returns authenticated user
        me_res = client.get("/api/auth/me")
        assert me_res.status_code == 200
        me_data = me_res.get_json()
        assert me_data["authenticated"] is True
        assert me_data["user"]["email"] == "priya@example.com"

    def test_api_logout_endpoint(self, client):
        client.post("/api/auth/register", json={
            "full_name": "Priya Sharma",
            "email": "priya@example.com",
            "password": "securepassword123"
        })
        client.post("/api/auth/login", json={
            "email": "priya@example.com",
            "password": "securepassword123"
        })
        
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        me_res = client.get("/api/auth/me")
        assert me_res.status_code == 200
        me_data = me_res.get_json()
        assert me_data["authenticated"] is False
        assert me_data["user"] is None
