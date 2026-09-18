"""Smart Agent Handoff — escalates a conversation to a human support agent.

Triggered either manually (user requests a human) or automatically by
chat.py (negative sentiment / repeated unanswerable questions).
"""

from .memory import get_raw_history, save_escalation
from .notify import send_email

# Must match the fallback wording in rag.py's system prompt.
NO_ANSWER_PHRASE = "I don't have enough information"

_REASON_LABELS = {
    "manual": "User requested a human agent",
    "user_requested_human": "User asked to speak with a human",
    "negative_sentiment": "High user frustration detected",
    "repeated_unanswered": "Bot could not answer repeated questions",
    "low_rating": "User rated a response 3 stars or lower",
}


def escalate(session_id: str, reason: str, extra_context: str | None = None) -> None:
    messages = get_raw_history(session_id)
    save_escalation(session_id, reason, messages)

    transcript = "\n\n".join(
        f"{'User' if m['type'] == 'human' else 'AdminIE'}: {m['content']}" for m in messages
    )
    label = _REASON_LABELS.get(reason, reason)
    body = f"Session ID: {session_id}\nReason: {label}\n"
    if extra_context:
        body += f"User feedback: {extra_context}\n"
    body += f"\n--- Transcript ---\n\n{transcript}"
    send_email(subject=f"AdminIE escalation — {label}", body=body)
