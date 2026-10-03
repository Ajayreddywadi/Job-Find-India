"""
services/auth_service.py — User Authentication & Profile Service
=================================================================
Handles user registration, credential verification, input validation,
password hashing, profile updates, and location preference management.
"""

from __future__ import annotations

import re
import logging
from typing import Any
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection
from models.user import User

logger = logging.getLogger("auth_service")

# Standard email format validation regex
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> bool:
    """Return True if email matches standard RFC email pattern."""
    if not email or not isinstance(email, str):
        return False
    return bool(_EMAIL_REGEX.match(email.strip()))


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password rules (minimum 6 characters)."""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, ""


def _row_to_user(row: Any) -> User:
    """Helper to convert database row to User object safely."""
    keys = row.keys() if hasattr(row, "keys") else []
    pref_loc = row["preferred_location"] if "preferred_location" in keys else ""
    return User(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        preferred_location=pref_loc or "",
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def register_user(full_name: str, email: str, password: str, preferred_location: str = "") -> tuple[dict[str, Any] | None, str]:
    """Register a new user in the database.

    Returns:
        (user_dict, error_message) tuple.
    """
    clean_name = (full_name or "").strip()
    clean_email = (email or "").strip().lower()
    clean_loc = (preferred_location or "").strip()

    if not clean_name:
        return None, "Full name is required."

    if not validate_email(clean_email):
        return None, "Invalid email address format."

    is_valid_pw, pw_err = validate_password(password)
    if not is_valid_pw:
        return None, pw_err

    # Check for existing duplicate email using parameterized query
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (clean_email,))
        if cursor.fetchone():
            return None, "An account with this email address already exists."

        # Generate secure password hash (NEVER store plain-text passwords)
        pw_hash = generate_password_hash(password)

        try:
            cursor.execute(
                "INSERT INTO users (full_name, email, password_hash, preferred_location) VALUES (?, ?, ?, ?)",
                (clean_name, clean_email, pw_hash, clean_loc),
            )
            conn.commit()
            user_id = cursor.lastrowid

            # Retrieve created user
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            user = _row_to_user(row)
            logger.info("Successfully registered new user: id=%d, email=%s", user.id, user.email)
            return user.to_dict(), ""
        except Exception as exc:
            logger.error("Error during user registration: %s", exc)
            return None, "Database error during registration."


def authenticate_user(email: str, password: str) -> tuple[dict[str, Any] | None, str]:
    """Authenticate user with email and password.

    Returns:
        (user_dict, error_message) tuple.
    """
    clean_email = (email or "").strip().lower()

    if not clean_email or not password:
        return None, "Email and password are required."

    if not validate_email(clean_email):
        return None, "Invalid email address format."

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE lower(email) = ?", (clean_email,))
        row = cursor.fetchone()

        if not row:
            return None, "Invalid email or password."

        # Verify password hash
        if not check_password_hash(row["password_hash"], password):
            return None, "Invalid email or password."

        user = _row_to_user(row)
        logger.info("User authenticated successfully: id=%d, email=%s", user.id, user.email)
        return user.to_dict(), ""


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Fetch user profile by user_id."""
    if not user_id:
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

        user = _row_to_user(row)
        return user.to_dict()


def update_user_location(user_id: int, preferred_location: str) -> tuple[dict[str, Any] | None, str]:
    """Update preferred job location for user."""
    if not user_id:
        return None, "User not authenticated."

    clean_loc = (preferred_location or "").strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET preferred_location = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (clean_loc, user_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None, "User not found."

        user = _row_to_user(row)
        return user.to_dict(), ""
