from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiosqlite, uuid
from datetime import datetime, timezone

app     = FastAPI(title="Context Bridge — Week 1 Complete")
DB_FILE = "week1.db"

@app.on_event("startup")
async def startup():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, title TEXT,
            created_at TEXT, updated_at TEXT, current_agent TEXT DEFAULT 'claude')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, role TEXT, content TEXT,
            agent TEXT, tokens_used INTEGER DEFAULT 0, timestamp TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS token_usage (
            session_id TEXT, agent TEXT, total_tokens INTEGER DEFAULT 0,
            PRIMARY KEY (session_id, agent))""")
        await db.commit()
    print("DB ready")

class CreateSessionReq(BaseModel):
    title: str = "New Chat"

class SaveMessageReq(BaseModel):
    session_id: str
    role:       str
    content:    str
    agent:      str = "claude"
    tokens:     int = 0

@app.post("/sessions")
async def create_session(body: CreateSessionReq):
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (sid, body.title, now, now, "claude"))
        await db.commit()
    return {"session_id": sid, "title": body.title}

@app.get("/sessions")
async def list_sessions():
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

@app.post("/messages")
async def save_message(body: SaveMessageReq):
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT INTO messages (session_id,role,content,agent,tokens_used,timestamp) VALUES (?,?,?,?,?,?)",
            (body.session_id, body.role, body.content, body.agent, body.tokens, now))
        await db.execute(
            "INSERT INTO token_usage VALUES (?,?,?) ON CONFLICT(session_id,agent) DO UPDATE SET total_tokens=total_tokens+?",
            (body.session_id, body.agent, body.tokens, body.tokens))
        await db.execute("UPDATE sessions SET updated_at=?,current_agent=? WHERE id=?",
            (now, body.agent, body.session_id))
        await db.commit()
    return {"saved": True}

@app.get("/messages/{session_id}")
async def get_messages(session_id: str):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute(
            "SELECT role,content,agent,tokens_used,timestamp FROM messages WHERE session_id=? ORDER BY id",
            (session_id,))
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

@app.get("/tokens/{session_id}")
async def get_tokens(session_id: str):
    LIMITS = {"claude": 10000, "gpt": 8000, "gemini": 15000}
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute(
            "SELECT agent,total_tokens FROM token_usage WHERE session_id=?", (session_id,))
        rows = await cur.fetchall()
    result = {}
    for r in rows:
        used  = r["total_tokens"]
        limit = LIMITS.get(r["agent"], 10000)
        result[r["agent"]] = {
            "used": used, "limit": limit,
            "percent":       round(used/limit*100, 1),
            "should_warn":   used > limit * 0.8,
            "should_switch": used > limit * 0.9,
        }
    return result

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        await db.execute("DELETE FROM token_usage WHERE session_id=?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        await db.commit()
    return {"deleted": session_id}

"""
WEEKEND CHALLENGE — try in /docs:
  1. POST /sessions → create a session, copy its session_id
  2. POST /messages → add 5-6 messages with tokens=300 each
  3. GET  /tokens/{id} → watch percent_used climb
  4. GET  /messages/{id} → see the full conversation
  5. DELETE /sessions/{id} → clean up
"""
