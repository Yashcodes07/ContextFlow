"""
backend/routers/sessions.py
----------------------------
STATUS: CREATE NEW

PURPOSE:
    Handles everything related to chat sessions — creating,
    listing, fetching messages, and deleting.

ROUTES:
    POST   /api/sessions/              create new session
    GET    /api/sessions/              list all sessions (sidebar)
    GET    /api/sessions/{id}/messages load conversation history
    DELETE /api/sessions/{id}          delete session + all its data
"""

from fastapi import APIRouter, HTTPException
import aiosqlite
import uuid
from datetime import datetime, timezone

from models.schemas import CreateSessionRequest, SessionResponse
from db.database import DB_PATH

router = APIRouter()


@router.post("/", response_model=SessionResponse)
async def create_session(body: CreateSessionRequest):
    """
    Creates a new chat session.
    Called when user clicks "New Chat" in the sidebar.
    """
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sessions
               (id, title, created_at, updated_at, current_agent)
               VALUES (?, ?, ?, ?, ?)""",
            (sid, body.title, now, now, "groq")
        )
        await db.commit()

    return SessionResponse(
        session_id=sid,
        title=body.title,
        created_at=now,
        current_agent="groq"
    )


@router.get("/")
async def list_sessions():
    """
    Returns all sessions ordered by most recent.
    Powers the session list in the left sidebar of the UI.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute(
            """SELECT id, title, created_at, updated_at, current_agent
               FROM sessions
               ORDER BY updated_at DESC"""
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    """
    Returns all messages in a session in order.
    Called when user clicks on an old session to resume it.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check session exists
        cur = await db.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        )
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        cur  = await db.execute(
            """SELECT role, content, agent, tokens_used, timestamp
               FROM messages
               WHERE session_id = ?
               ORDER BY id ASC""",
            (session_id,)
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Deletes a session and ALL its messages and token records.
    This is a cascading delete — one call cleans everything.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM messages    WHERE session_id = ?", (session_id,)
        )
        await db.execute(
            "DELETE FROM token_usage WHERE session_id = ?", (session_id,)
        )
        await db.execute(
            "DELETE FROM sessions    WHERE id = ?", (session_id,)
        )
        await db.commit()

    return {"deleted": True, "session_id": session_id}