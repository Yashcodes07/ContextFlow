"""
backend/routers/chat.py
------------------------
STATUS: CREATE NEW

PURPOSE:
    The most important router — handles every chat message.
    This is the route the frontend calls when user hits Send.

    Flow for every message:
      1. Load conversation history from DB
      2. Load context summary (if agent was switched before)
      3. Build system prompt (with or without context)
      4. Call Groq API
      5. Save user message + AI reply to DB
      6. Update token usage in DB
      7. Auto-summarize if token usage crosses 75%
      8. Return reply + token status to frontend

ROUTES:
    POST /api/chat/   send a message, get AI reply + token status
"""

from fastapi import APIRouter, HTTPException
import aiosqlite
from datetime import datetime, timezone

from models.schemas import SendMessageRequest, SendMessageResponse
from services.groq_service import (
    call_agent,
    summarize_context,
    build_system_prompt,
    get_token_status,
)
from db.database import DB_PATH

router = APIRouter()


@router.post("/", response_model=SendMessageResponse)
async def send_message(body: SendMessageRequest):
    """
    Main chat endpoint — called every time user sends a message.
    """
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── 1. Check session exists ──────────────────────────
        cur = await db.execute(
            "SELECT context_summary FROM sessions WHERE id = ?",
            (body.session_id,)
        )
        session = await cur.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        context_summary = session["context_summary"]

        # ── 2. Load last 20 messages as history ──────────────
        cur = await db.execute(
            """SELECT role, content FROM messages
               WHERE session_id = ?
               ORDER BY id DESC LIMIT 20""",
            (body.session_id,)
        )
        rows    = await cur.fetchall()
        history = list(reversed([dict(r) for r in rows]))

        # ── 3. Get current token usage for this agent ────────
        cur = await db.execute(
            """SELECT total_tokens FROM token_usage
               WHERE session_id = ? AND agent = ?""",
            (body.session_id, body.agent)
        )
        usage_row    = await cur.fetchone()
        tokens_so_far = usage_row["total_tokens"] if usage_row else 0

    # ── 4. Build messages list for API call ──────────────────
    messages = history + [{"role": "user", "content": body.message}]
    system   = build_system_prompt(context_summary)

    # ── 5. Call the AI ───────────────────────────────────────
    try:
        result = await call_agent(body.agent, messages, system, body.api_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # ── 6. Calculate new token total ─────────────────────────
    new_total = tokens_so_far + result["tokens"]
    status    = get_token_status(new_total, body.agent)

    # ── 7. Save everything to DB ─────────────────────────────
    async with aiosqlite.connect(DB_PATH) as db:

        # Save user message
        await db.execute(
            """INSERT INTO messages
               (session_id, role, content, agent, tokens_used, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (body.session_id, "user", body.message, body.agent, 0, now)
        )

        # Save AI reply
        await db.execute(
            """INSERT INTO messages
               (session_id, role, content, agent, tokens_used, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (body.session_id, "assistant", result["content"],
             body.agent, result["tokens"], now)
        )

        # Update token usage (INSERT or UPDATE)
        await db.execute(
            """INSERT INTO token_usage (session_id, agent, total_tokens)
               VALUES (?, ?, ?)
               ON CONFLICT(session_id, agent)
               DO UPDATE SET total_tokens = ?""",
            (body.session_id, body.agent, new_total, new_total)
        )

        # Update session metadata
        await db.execute(
            """UPDATE sessions
               SET updated_at = ?, current_agent = ?
               WHERE id = ?""",
            (now, body.agent, body.session_id)
        )

        # ── 8. Auto-summarize at 75% token usage ─────────────
        if status["should_summarize"] and not context_summary:
            all_msgs = messages + [
                {"role": "assistant", "content": result["content"]}
            ]
            try:
                summary = await summarize_context(all_msgs, body.api_key)
                await db.execute(
                    "UPDATE sessions SET context_summary = ? WHERE id = ?",
                    (summary, body.session_id)
                )
            except Exception:
                pass  # summarization failure should not block the chat

        await db.commit()

    return SendMessageResponse(
        reply=result["content"],
        agent=body.agent,
        tokens_used=result["tokens"],
        **status,
    )