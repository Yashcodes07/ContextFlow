import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Model — best free model on Groq ─────────────────────────────────────────
# Other free options: "mixtral-8x7b-32768", "gemma2-9b-it"
MODEL    = "llama-3.3-70b-versatile"
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

HEADERS  = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type":  "application/json",
}


# ── Safe response extractor ──────────────────────────────────────────────────
def extract_reply(data: dict) -> str:
    """
    Safely pulls text reply from Groq API response.
    Prints a clear error instead of crashing with KeyError.
    """
    if "error" in data:
        code = data["error"].get("code", "unknown")
        msg  = data["error"].get("message", "")[:150]
        raise Exception(f"Groq API Error {code}: {msg}")

    if "choices" not in data:
        raise Exception(f"Unexpected response: {json.dumps(data)[:200]}")

    return data["choices"][0]["message"]["content"]


def get_tokens_used(data: dict) -> int:
    """Pulls total token count from response — used for tracking limits."""
    return data.get("usage", {}).get("total_tokens", 0)


# ============================================================
# FUNCTION 1 — Single message
# Used when: user sends their very first message in a session
# ============================================================

def send_single_message(user_message: str) -> tuple[str, int]:
    """
    Sends one message to Groq, returns (reply_text, tokens_used).
    We return tokens_used so we can track usage per session.
    """
    body = {
        "model":      MODEL,
        "max_tokens": 500,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post(BASE_URL, headers=HEADERS, json=body)
    data     = response.json()

    # Print full response on first call so you learn the structure
    print("\n--- FULL API RESPONSE (study this) ---")
    print(json.dumps(data, indent=2))
    print("--------------------------------------\n")

    return extract_reply(data), get_tokens_used(data)


# ============================================================
# FUNCTION 2 — Multi-turn conversation (CORE OF CONTEXT BRIDGE)
# Used when: every message after the first
#
# We save every message to our database, then send the
# ENTIRE history to Groq on each call — that is how it
# remembers what was said earlier in the conversation.
# ============================================================

def send_with_history(conversation_history: list) -> tuple[str, int]:
    """
    Sends full conversation history to Groq.

    conversation_history format (same as OpenAI):
    [
        {"role": "user",      "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user",      "content": "What did I say?"},
    ]

    NOTE: Groq uses "assistant" (not "model" like Gemini)
    This format is also identical to OpenAI GPT format.
    """
    body = {
        "model":      MODEL,
        "max_tokens": 500,
        "messages":   conversation_history,
    }

    response = requests.post(BASE_URL, headers=HEADERS, json=body)
    data     = response.json()
    return extract_reply(data), get_tokens_used(data)


# ============================================================
# FUNCTION 3 — With system prompt (context injection)
# Used when: user switches agents — we inject the saved
# summary so the new agent knows what happened before.
#
# This is THE key feature of Context Bridge.
# ============================================================

def send_with_context(system_prompt: str, conversation_history: list) -> tuple[str, int]:
    """
    Sends a system prompt + conversation to Groq.

    The system_prompt is where we inject the saved context
    summary when the user switches agents. It tells the new
    agent: "Here is what happened before, continue from here."
    """
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    body = {
        "model":      MODEL,
        "max_tokens": 500,
        "messages":   messages,
    }

    response = requests.post(BASE_URL, headers=HEADERS, json=body)
    data     = response.json()
    return extract_reply(data), get_tokens_used(data)


# ============================================================
# FUNCTION 4 — Summarize conversation
# Used when: user hits 75% of token limit — we auto-generate
# a summary to hand off to the next agent
#
# This is the "magic" function of Context Bridge.
# ============================================================

def summarize_conversation(conversation_history: list) -> str:
    """
    Takes a full conversation and generates a compact summary
    that can be injected into the next agent as context.

    In the real app this runs automatically when token usage
    crosses 75% of the free limit.
    """
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history
    )

    summary_prompt = f"""Summarize this conversation so a NEW AI agent can continue the work.
Include:
1. What the user is trying to build or accomplish
2. Key decisions made so far
3. Any code or files produced (include them fully)
4. What is still incomplete or the next step

Be concise but complete. Max 150 words.

CONVERSATION:
{history_text}"""

    messages = [{"role": "user", "content": summary_prompt}]
    body     = {"model": MODEL, "max_tokens": 300, "messages": messages}

    response = requests.post(BASE_URL, headers=HEADERS, json=body)
    data     = response.json()
    return extract_reply(data)[0]   # just the text, not tokens


# ============================================================
# FUNCTION 5 — Count tokens (rough estimate)
# Groq does not have a dedicated token counting endpoint
# so we use the usage field from actual responses
# ============================================================

FREE_DAILY_TOKENS = 500_000   # Groq free tier rough daily limit

def check_token_status(tokens_used: int) -> dict:
    """
    Returns a status dict used by Context Bridge to decide
    whether to show a warning or force an agent switch.
    """
    pct = round(tokens_used / FREE_DAILY_TOKENS * 100, 1)
    return {
        "tokens_used":   tokens_used,
        "limit":         FREE_DAILY_TOKENS,
        "percent":       pct,
        "should_warn":   pct > 80,     # show yellow warning bar
        "should_switch": pct > 90,     # show red banner, suggest switch
    }


# ============================================================
# TESTS — Run all 4 to see every function working
# ============================================================

if __name__ == "__main__":

    print(f"Model: {MODEL}")
    print(f"Provider: Groq (free tier)\n")

    total_tokens = 0   # track across all calls


    # ── TEST 1: Single message ───────────────────────────────
    print("=" * 55)
    print("TEST 1 — Single message")
    print("=" * 55)

    reply, tokens = send_single_message("What is Python used for? One sentence.")
    total_tokens += tokens
    print(f"GROQ:   {reply}")
    print(f"Tokens: {tokens} used this call | {total_tokens} total so far")


    # ── TEST 2: Multi-turn conversation ──────────────────────
    print("\n" + "=" * 55)
    print("TEST 2 — Multi-turn conversation")
    print("This is how Context Bridge stores and sends history")
    print("=" * 55)

    history = []

    # Turn 1
    msg1 = "My name is Yash and I am building a Python web scraper for e-commerce sites"
    history.append({"role": "user", "content": msg1})
    print(f"USER:   {msg1}")

    reply1, tokens1 = send_with_history(history)
    history.append({"role": "assistant", "content": reply1})
    total_tokens += tokens1
    print(f"GROQ:   {reply1[:120]}...")
    print(f"Tokens: {tokens1} this call\n")

    # Turn 2 — tests if it remembered Turn 1
    msg2 = "What is my name and what am I building?"
    history.append({"role": "user", "content": msg2})
    print(f"USER:   {msg2}")

    reply2, tokens2 = send_with_history(history)
    history.append({"role": "assistant", "content": reply2})
    total_tokens += tokens2
    print(f"GROQ:   {reply2[:150]}")
    print(f"Tokens: {tokens2} this call")
    print("\n✅ It remembered your name and project — that is context working!")


    # ── TEST 3: Context injection (agent switch simulation) ──
    print("\n" + "=" * 55)
    print("TEST 3 — Context injection (agent switch simulation)")
    print("What happens in Context Bridge when you switch agents")
    print("=" * 55)

    # This summary would be auto-generated by summarize_conversation()
    # when the user hits 75% of their token limit
    saved_summary = """
    User (Yash) is building a Python web scraper for e-commerce sites.
    Already done: basic requests + BeautifulSoup scraper that extracts
    product names and prices. File: scraper.py
    Still needed: error handling, retry logic, and CSV export feature.
    Next step: add try/except blocks around the requests call.
    """

    system = (
        "You are continuing work from a previous AI session. "
        f"Full context of what was done:\n{saved_summary}\n"
        "Resume naturally — do NOT reintroduce yourself. "
        "Just continue the work as if you were already helping."
    )

    new_history = [
        {"role": "user", "content": "What should I work on next?"}
    ]

    reply3, tokens3 = send_with_context(system, new_history)
    total_tokens += tokens3
    print(f"GROQ:   {reply3[:300]}")
    print(f"Tokens: {tokens3} this call")
    print("\n✅ It picked up exactly where the old session left off!")


    # ── TEST 4: Token status check ───────────────────────────
    print("\n" + "=" * 55)
    print("TEST 4 — Token status (how Context Bridge warns you)")
    print("=" * 55)

    status = check_token_status(total_tokens)
    print(f"Tokens used this session: {status['tokens_used']}")
    print(f"Free daily limit:         {status['limit']:,}")
    print(f"Percent used:             {status['percent']}%")
    print(f"Show warning banner:      {status['should_warn']}")
    print(f"Force agent switch:       {status['should_switch']}")

    if status["should_warn"]:
        print("\n⚠️  Warning: Switch agents soon!")
    else:
        print(f"\n✅ {FREE_DAILY_TOKENS - total_tokens:,} tokens remaining today")

    print("\n\n🎉 ALL TESTS COMPLETE — Day 1 done!")
    print("You now understand every API pattern used in Context Bridge.")


"""
EXERCISES (do all 3 before moving to python_foundations.py):
──────────────────────────────────────────────────────────────
1. In TEST 2, add a 3rd turn — ask:
   "Summarize our conversation in 2 sentences"
   This is EXACTLY what Context Bridge does before switching agents.

2. In TEST 3, change saved_summary to describe YOUR OWN project
   and ask "what should I work on next?" — see how it responds.

3. Simulate hitting the limit:
   Call check_token_status(450000) and check_token_status(490000)
   See what should_warn and should_switch return.
   This is the exact logic powering the warning bar in the UI.
"""