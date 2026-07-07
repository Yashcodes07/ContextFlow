"""
backend/routers/context.py
---------------------------
STATUS: CREATE NEW

PURPOSE:
    Handles agent switching and context inspection.
    When user clicks "Switch to Groq" (or another agent),
    this router saves the context summary and updates the session.

ROUTES:
    POST /api/context/switch          manually trigger agent switch
    GET  /api/context/{id}/summary    view saved context summary
    GET  /api/context/{id}/tokens     get token usage per agent
"""

from fastapi import APIRouter, HTTPException
import aiosqlite
from datetime import datetime, timezone

from models.schemas import SwitchAgentRequest, SwitchAgentResponse
from services.groq_service import summarize_context
from db.database import DB_PATH

router = APIRouter()


@router.post("/switch", response_model=SwitchAgentResponse)
async def switch_agent(body: SwitchAgentRequest):
    """
    Saves a context summary and switches the active agent.

    Called when:
      - User manually clicks a different agent tab
      - Token usage hits 90% (auto-triggered from frontend)

    Steps:
      1. Load last 30 messages from DB
      2. Generate context summary via Groq
      3. Save summary to sessions table
      4. Update current_agent in sessions table
      5. Return summary so frontend can show it
    """
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Load recent messages for summarization
        cur = await db.execute(
            """SELECT role, content FROM messages
               WHERE session_id = ?
               ORDER BY id DESC LIMIT 30""",
            (body.session_id,)
        )
        rows = await cur.fetchall()

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="No messages to summarize — start a conversation first"
        )

    history = list(reversed([dict(r) for r in rows]))

    # Generate the handoff summary
    try:
        summary = await summarize_context(history, body.api_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Summary failed: {str(e)}")

    # Save summary + update agent
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE sessions
               SET context_summary = ?, current_agent = ?, updated_at = ?
               WHERE id = ?""",
            (summary, body.new_agent, now, body.session_id)
        )
        await db.commit()

    return SwitchAgentResponse(
        session_id=body.session_id,
        new_agent=body.new_agent,
        summary=summary,
    )


@router.get("/{session_id}/summary")
async def get_summary(session_id: str):
    """
    Returns the saved context summary for a session.
    Used by the frontend to show "Context saved" preview.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT context_summary FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = await cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "summary":    row["context_summary"],
        "has_summary": row["context_summary"] is not None,
    }


@router.get("/{session_id}/tokens")
async def get_token_usage(session_id: str):
    """
    Returns token usage per agent for a session.
    Powers the token usage bars in the frontend sidebar.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT agent, total_tokens
               FROM token_usage
               WHERE session_id = ?""",
            (session_id,)
        )
        rows = await cur.fetchall()

    TOKEN_LIMITS = {"groq": 500_000}
    result = {}

    for r in rows:
        agent = r["agent"]
        used  = r["total_tokens"]
        limit = TOKEN_LIMITS.get(agent, 500_000)
        result[agent] = {
            "used":          used,
            "limit":         limit,
            "percent":       round(used / limit * 100, 2),
            "should_warn":   used > limit * 0.80,
            "should_switch": used > limit * 0.90,
        }

    return result