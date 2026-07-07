"""
backend/db/database.py
-----------------------
STATUS: CREATE NEW

PURPOSE:
    Single place that owns the database connection and table
    creation. Every router imports get_db() from here.

    Tables:
      sessions     — one row per conversation
      messages     — one row per message
      token_usage  — tracks tokens per agent per session
"""

import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "contextflow.db")


async def init_db():
    """
    Called once at server startup.
    Creates all tables if they don't already exist.
    """
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              TEXT PRIMARY KEY,
                title           TEXT,
                created_at      TEXT,
                updated_at      TEXT,
                current_agent   TEXT DEFAULT 'groq',
                context_summary TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                agent       TEXT    NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                timestamp   TEXT    NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                session_id   TEXT NOT NULL,
                agent        TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                PRIMARY KEY (session_id, agent)
            )
        """)

        await db.commit()
    print("✅ Database ready — contextflow.db")


async def get_db():
    """Yields a database connection for use in route handlers."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db