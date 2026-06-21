import sqlite3
import uuid
from datetime import datetime, timezone

DB_FILE = "practice.db"

def init_database():
    """Creates tables if they don't already exist."""
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    # sessions table — one row = one conversation
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id              TEXT PRIMARY KEY,
            title           TEXT,
            created_at      TEXT,
            updated_at      TEXT,
            current_agent   TEXT DEFAULT 'claude',
            context_summary TEXT
        )
    """)

    # messages table — one row = one message
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT,
            role        TEXT,       -- 'user' or 'assistant'
            content     TEXT,
            agent       TEXT,       -- 'claude', 'gpt', 'gemini'
            tokens_used INTEGER DEFAULT 0,
            timestamp   TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # token_usage table — tracks how many tokens each agent used per session
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            session_id   TEXT,
            agent        TEXT,
            total_tokens INTEGER DEFAULT 0,
            PRIMARY KEY (session_id, agent)
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready")


def create_session(title: str) -> str:
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?,?,?,?)",
        (sid, title, now, now)
    )
    conn.commit()
    conn.close()
    print(f"Created session: {sid[:8]}... — '{title}'")
    return sid


def save_message(session_id: str, role: str, content: str, agent: str, tokens: int = 0):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO messages (session_id,role,content,agent,tokens_used,timestamp) VALUES (?,?,?,?,?,?)",
        (session_id, role, content, agent, tokens, now)
    )
    conn.execute(
        "INSERT INTO token_usage (session_id,agent,total_tokens) VALUES (?,?,?) "
        "ON CONFLICT(session_id,agent) DO UPDATE SET total_tokens=total_tokens+?",
        (session_id, agent, tokens, tokens)
    )
    conn.execute(
        "UPDATE sessions SET updated_at=?, current_agent=? WHERE id=?",
        (now, agent, session_id)
    )
    conn.commit()
    conn.close()


def get_messages(session_id: str) -> list:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT role,content,agent,tokens_used FROM messages WHERE session_id=? ORDER BY id",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_token_usage(session_id: str) -> dict:
    LIMITS = {"claude": 10000, "gpt": 8000, "gemini": 15000}
    conn   = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows   = conn.execute(
        "SELECT agent, total_tokens FROM token_usage WHERE session_id=?",
        (session_id,)
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        agent = r["agent"]
        used  = r["total_tokens"]
        limit = LIMITS.get(agent, 10000)
        result[agent] = {"used": used, "limit": limit, "percent": round(used/limit*100, 1)}
    return result


if __name__ == "__main__":
    init_database()

    sid = create_session("Build a Python web scraper")
    save_message(sid, "user",      "Help me build a web scraper",               "claude", 12)
    save_message(sid, "assistant", "Sure! Here is a basic scraper...",           "claude", 85)
    save_message(sid, "user",      "Now add error handling",                     "claude", 8)
    save_message(sid, "assistant", "Here is the updated version with try/except", "claude", 120)

    print("\nConversation:")
    for m in get_messages(sid):
        print(f"  [{m['agent']}] {m['role'].upper()}: {m['content'][:55]}")

    print("\nToken usage:")
    for agent, info in get_token_usage(sid).items():
        print(f"  {agent}: {info['used']} tokens ({info['percent']}%)")

"""
EXERCISES:
  1. Create a second session and add GPT messages to it
  2. Write list_all_sessions() that returns all rows from sessions table
  3. Write delete_session(session_id) that removes the session and its messages
"""
