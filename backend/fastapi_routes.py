from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Context Bridge — Day 3 Practice")

@app.get("/")
def root():
    return {"message": "Context Bridge API is running!"}

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name}! Welcome to Context Bridge."}

# POST with a request body — Pydantic validates the data automatically
class EchoRequest(BaseModel):
    text: str
    repeat: int = 1  

@app.post("/echo")
def echo(body: EchoRequest):
    result = (body.text + " ") * body.repeat
    return {"echoed": result.strip(), "length": len(result)}

# Simulated chat — no real API call yet, just fake replies
class FakeChatRequest(BaseModel):
    message: str
    agent: str = "claude"

@app.post("/api/chat/fake")
def fake_chat(body: FakeChatRequest):
    fake_replies = {
        "claude": f"[Claude] Got: '{body.message}'",
        "gpt":    f"[GPT]    Got: '{body.message}'",
        "gemini": f"[Gemini] Got: '{body.message}'",
    }
    return {
        "reply":       fake_replies.get(body.agent, "Unknown agent"),
        "agent":       body.agent,
        "tokens_used": len(body.message) // 4,
    }

# In-memory token tracker (resets when server restarts — DB fixes this in Day 4)
token_store: dict = {}

@app.post("/api/tokens/add")
def add_tokens(session_id: str, agent: str, tokens: int):
    if session_id not in token_store:
        token_store[session_id] = {"claude": 0, "gpt": 0, "gemini": 0}
    token_store[session_id][agent] += tokens
    used  = token_store[session_id][agent]
    limit = {"claude": 10000, "gpt": 8000, "gemini": 15000}[agent]
    return {
        "used": used, "limit": limit,
        "percent":       round(used / limit * 100, 1),
        "should_warn":   used > limit * 0.8,
        "should_switch": used > limit * 0.9,
    }

@app.get("/api/tokens/{session_id}")
def get_tokens(session_id: str):
    return token_store.get(session_id, {"error": "Session not found"})

@app.get("/api/agents")
def get_agents():
   
    return ["claude", "gpt", "gemini"]  


