"""
backend/main.py
DAY: Monday | STATUS: EDIT — update title and version only

CHANGES FROM WEEK 2:
    - Version bumped to 2.0.0
    - Shows supported agents in root response
    - Everything else stays the same
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from routers import sessions, chat, context

app = FastAPI(
    title="ContextFlow API",
    description="Multi-agent AI context bridge — switch agents without losing work",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()

app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(chat.router,     prefix="/api/chat",     tags=["Chat"])
app.include_router(context.router,  prefix="/api/context",  tags=["Context"])

@app.get("/")
def root():
    return {
        "project":         "ContextFlow",
        "version":         "2.0.0",
        "status":          "running",
        "docs":            "/docs",
        "agents_supported": ["groq", "openai", "gemini"],
    }