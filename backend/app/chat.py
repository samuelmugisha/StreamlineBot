"""Chat endpoint logic — wires memory + RAG graph together."""

import os
import re

from langchain_core.messages import AIMessage, BaseMessage

from .rag import run_rag
from .memory import load_window, save_exchange
from .schemas import ChatRequest, ChatResponse
from .sentiment import analyze_message
from .escalation import escalate, NO_ANSWER_PHRASE

_GREETING_RE = re.compile(
    r"^\s*(hi+|hello+|hey+|good\s+(morning|afternoon|evening|day)|howdy|greetings?|what'?s?\s*up)\W*\s*$",
    re.IGNORECASE,
)
_COMPANY = os.environ.get("COMPANY_NAME", "AdminIE")
_GREETING_REPLY = f"Hello! I'm the {_COMPANY} support assistant. How can I help you today?"

_SENTIMENT_THRESHOLD = int(os.environ.get("SENTIMENT_ESCALATION_THRESHOLD", 4))
_NO_ANSWER_STREAK_THRESHOLD = int(os.environ.get("NO_ANSWER_STREAK_THRESHOLD", 2))


def _no_answer_streak(history: list[BaseMessage], answer: str) -> int:
    """Count consecutive un-answerable bot replies, including the current one."""
    if NO_ANSWER_PHRASE not in answer:
        return 0
    streak = 1
    for msg in reversed(history):
        if isinstance(msg, AIMessage):
            if NO_ANSWER_PHRASE in msg.content:
                streak += 1
            else:
                break
    return streak


def handle_chat(request: ChatRequest) -> ChatResponse:
    history = load_window(request.session_id, k=10)

    if _GREETING_RE.match(request.message):
        answer, tutorial = _GREETING_REPLY, None
    else:
        result   = run_rag(question=request.message, history=history)
        answer   = result["answer"]
        tutorial = result["tutorial"]

    # Don't link to a tutorial page for a question the bot couldn't answer —
    # the linked page is unrelated to what the user actually asked.
    if NO_ANSWER_PHRASE in answer:
        tutorial = None

    previous_answer = history[-1].content if history and isinstance(history[-1], AIMessage) else ""
    analysis = analyze_message(request.message, previous_answer=previous_answer)

    save_exchange(
        session_id=request.session_id,
        user_message=request.message,
        ai_message=answer,
        sentiment=analysis.frustration,
    )

    escalation_reason = None
    if analysis.wants_human:
        escalation_reason = "user_requested_human"
    elif analysis.frustration >= _SENTIMENT_THRESHOLD:
        escalation_reason = "negative_sentiment"
    elif _no_answer_streak(history, answer) >= _NO_ANSWER_STREAK_THRESHOLD:
        escalation_reason = "repeated_unanswered"

    escalated = False
    if escalation_reason:
        escalate(request.session_id, reason=escalation_reason)
        escalated = True

    return ChatResponse(session_id=request.session_id, answer=answer, escalated=escalated, tutorial=tutorial)
