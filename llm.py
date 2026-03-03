"""LLM module using Groq API (free, fast inference)."""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a helpful, friendly voice assistant. Keep your responses concise \
and conversational — typically 1-3 sentences. You're speaking out loud, so avoid \
markdown, bullet points, code blocks, or any formatting. Be natural, warm, and direct. \
If you don't know something, say so honestly."""

_client = None


def get_client() -> Groq:
    """Lazy-load the Groq client."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")
        _client = Groq(api_key=api_key)
        print("[LLM] Groq client initialized.")
    return _client


def chat(user_message: str, history: list[dict] | None = None) -> str:
    """
    Send a message to the LLM and get a response.

    Args:
        user_message: The user's transcribed speech.
        history: Optional conversation history (list of role/content dicts).

    Returns:
        The assistant's response text.
    """
    client = get_client()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_completion_tokens=256,
    )

    reply = response.choices[0].message.content.strip()
    print(f"[LLM] Response: {reply}")
    return reply
