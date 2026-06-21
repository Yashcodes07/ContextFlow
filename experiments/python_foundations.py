"""
DAY 2 — Python Concepts You Need for This Project
---------------------------------------------------
Run each section one at a time. Read every comment.
"""

import asyncio

# =========================================================
# SECTION 1 — DICTIONARIES
# Every API request and response is a dictionary
# =========================================================

message = {
    "role": "user",
    "content": "Help me write a web scraper",
    "agent": "claude",
    "tokens_used": 150
}

print("=== DICTIONARIES ===")
print(message["role"])           # user
print(message["content"])        # Help me write a web scraper
message["tokens_used"] = 200     # update
print(message)

# =========================================================
# SECTION 2 — LIST OF DICTS (how a conversation is stored)
# =========================================================

conversation = [
    {"role": "user",      "content": "Hello!"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user",      "content": "Write me a for loop in Python"},
    {"role": "assistant", "content": "Sure! Here's a for loop..."},
]

print("\n=== CONVERSATION ===")
for msg in conversation:
    print(f"  {msg['role'].upper()}: {msg['content']}")

# Get only user messages using list comprehension
user_msgs = [m for m in conversation if m["role"] == "user"]
print(f"\nUser sent {len(user_msgs)} messages")

# =========================================================
# SECTION 3 — FUNCTIONS
# =========================================================

def count_tokens_rough(text: str) -> int:
    """1 token is roughly 4 characters — rough but good enough for tracking."""
    return len(text) // 4

def build_system_prompt(agent_name: str, context_summary: str = None) -> str:
    """
    Builds the instruction we send to an AI before the conversation.
    context_summary is optional — used only when switching agents.
    """
    base = f"You are {agent_name}, a helpful AI assistant."
    if context_summary:
        base += f"\n\nYou are CONTINUING previous work. Context:\n{context_summary}"
    return base

print("\n=== FUNCTIONS ===")
print(count_tokens_rough("Hello world this is a test sentence"))
print(build_system_prompt("Claude"))
print(build_system_prompt("GPT-4o", "User was building a Python web scraper"))

# =========================================================
# SECTION 4 — ASYNC / AWAIT
# Used in FastAPI so the server can handle multiple users at once
# =========================================================

async def fake_api_call(agent: str, message: str) -> str:
    await asyncio.sleep(0.5)   # pretend we waited for an API response
    return f"[{agent}] Response to: '{message}'"

async def main():
    print("\n=== ASYNC — calling two agents at the same time ===")
    # asyncio.gather runs both at once instead of one-after-another
    results = await asyncio.gather(
        fake_api_call("Claude", "Hello"),
        fake_api_call("GPT",   "Hello"),
    )
    for r in results:
        print(r)

asyncio.run(main())

# =========================================================
# SECTION 5 — F-STRINGS (used constantly)
# =========================================================

agent   = "Claude"
used    = 1500
limit   = 10000
pct     = round(used / limit * 100, 1)

print("\n=== F-STRINGS ===")
print(f"Agent: {agent}")
print(f"Tokens: {used}/{limit} ({pct}%)")
print(f"Status: {'⚠️ Warning' if pct > 80 else '✅ OK'}")

"""
EXERCISES:
  1. Add 4 more messages to `conversation` and loop through them
  2. Write a function that takes a conversation list and counts total tokens
  3. Make build_system_prompt also accept the current_agent name as a parameter
"""
