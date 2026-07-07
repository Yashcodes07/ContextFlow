"""
backend/models/schemas.py
--------------------------
STATUS: CREATE NEW

PURPOSE:
    Defines the shape of every request and response in our API.
    Pydantic validates data automatically — wrong data gets
    rejected before it even reaches our code.
"""

from pydantic import BaseModel
from typing import Optional


class CreateSessionRequest(BaseModel):
    title: str = "New Chat"

class SessionResponse(BaseModel):
    session_id:    str
    title:         str
    created_at:    str
    current_agent: str = "groq"

class SendMessageRequest(BaseModel):
    session_id: str
    message:    str
    agent:      str = "groq"
    api_key:    str               # user's own key — never stored in DB

class SendMessageResponse(BaseModel):
    reply:         str
    agent:         str
    tokens_used:   int
    token_total:   int
    token_limit:   int
    percent_used:  float
    should_warn:   bool           # True at 80%
    should_switch: bool           # True at 90%

class SwitchAgentRequest(BaseModel):
    session_id: str
    new_agent:  str
    api_key:    str

class SwitchAgentResponse(BaseModel):
    session_id: str
    new_agent:  str
    summary:    str

class MessageRecord(BaseModel):
    role:        str
    content:     str
    agent:       str
    tokens_used: int
    timestamp:   str