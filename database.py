"""
database.py — SQLite Database Connection & Schema Management
==============================================================
Manages SQLite database connections, automatic schema initialization,
and parameterized query execution for the Job Find India application.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

import config.settings

logger = logging.getLogger("database")

def get_db_connection() -> sqlite3.Connection:
    """Create and return a row-factory-enabled SQLite connection."""
    db_path = Path(config.settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Enable Foreign Key support
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    """Initialize SQLite database tables if they do not exist."""
    db_path = Path(config.settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("Initializing database at %s", db_path)
    
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        preferred_location TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """
    
    with get_db_connection() as conn:
        conn.executescript(schema)
        # Handle schema migration for pre-existing databases
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "preferred_location" not in cols:
            logger.info("Migrating schema: adding preferred_location column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_location TEXT DEFAULT ''")
        conn.commit()
        
    logger.info("Database schema initialized successfully")
