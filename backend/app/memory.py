"""
Conversation memory — Supabase REST API with a module-level singleton client.
One client is created at import time and reused across all requests.
Supabase operations are retried on transient network errors.
"""

import os
from functools import lru_cache

import httpx
from supabase import create_client, Client
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_RETRY = dict(
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    wait=wait_exponential(multiplier=0.5, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)


@lru_cache(maxsize=1)
def _client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


@retry(**_SUPABASE_RETRY)
def load_window(session_id: str, k: int = 10) -> list[BaseMessage]:
    """Return the most recent k turn-pairs (human + ai) in chronological order."""
    result = (
        _client()
        .table("chat_history")
        .select("message")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(k * 2)
        .execute()
    )
    messages: list[BaseMessage] = []
    for row in reversed(result.data):
        msg = row["message"]
        if msg["type"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    return messages


@retry(**_SUPABASE_RETRY)
def save_exchange(session_id: str, user_message: str, ai_message: str, sentiment: int | None = None) -> None:
    human_row = {"session_id": session_id, "message": {"type": "human", "content": user_message}}
    if sentiment is not None:
        human_row["sentiment"] = sentiment
    _client().table("chat_history").insert([
        human_row,
        {"session_id": session_id, "message": {"type": "ai", "content": ai_message}},
    ]).execute()


@retry(**_SUPABASE_RETRY)
def save_feedback(session_id: str, question: str, answer: str, rating: int, comment: str | None = None) -> None:
    row = {"session_id": session_id, "question": question, "answer": answer, "rating": rating}
    if comment:
        row["comment"] = comment
    _client().table("message_feedback").insert(row).execute()


@retry(**_SUPABASE_RETRY)
def save_escalation(session_id: str, reason: str, transcript: list[dict]) -> None:
    _client().table("escalations").insert({
        "session_id": session_id,
        "reason": reason,
        "transcript": transcript,
    }).execute()


@retry(**_SUPABASE_RETRY)
def get_raw_history(session_id: str) -> list[dict]:
    """Return full message history in chronological order for the /history endpoint."""
    result = (
        _client()
        .table("chat_history")
        .select("message, created_at")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return [row["message"] for row in result.data]
