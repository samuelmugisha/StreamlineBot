"""Keyword-based message analysis — zero LLM calls, zero quota usage.

Scores frustration and detects requests to speak with a human, both used to
decide when a conversation should be escalated (see escalation.py).
"""

import re

from pydantic import BaseModel, Field


class MessageAnalysis(BaseModel):
    frustration: int = Field(
        description="How frustrated or upset the user sounds, from 1 (calm/neutral) to 5 (very frustrated or angry)."
    )
    wants_human: bool = Field(
        description=(
            "True if the user is asking to speak with a human, agent, or support team — "
            "either directly, or by agreeing to the assistant's offer to forward them to support."
        )
    )


_HUMAN_RE = re.compile(
    r"\b("
    r"human|agent|representative|rep|real\s+person|"
    r"talk\s+to\s+(a\s+)?(human|person|agent|someone)|"
    r"speak\s+(to|with)\s+(a\s+)?(human|person|agent|someone)|"
    r"connect\s+me|customer\s+(service|support)|live\s+(chat|agent|support)"
    r")\b",
    re.IGNORECASE,
)

_AGREEMENT_RE = re.compile(
    r"^\s*(yes|yeah|yep|sure|ok|okay|please|yes\s+please|go\s+ahead|"
    r"do\s+that|that\s+(would\s+be\s+)?great|sounds?\s+good)\W*\s*$",
    re.IGNORECASE,
)

# Substring from the bot's no-answer reply (must stay in sync with rag.py system prompt).
_ESCALATION_OFFER = "notify our support team"

_FRUSTRATION_RE = re.compile(
    r"\b("
    r"frustrated?|frustrating|annoyed?|annoying|angry|useless|stupid|"
    r"terrible|awful|horrible|doesn'?t\s+work|not\s+working|broken|"
    r"ridiculous|pathetic|rubbish|trash|garbage|hate|worst|wrong|"
    r"unacceptable|disappointing|disappointed|fed\s+up|sick\s+of|tired\s+of"
    r")\b",
    re.IGNORECASE,
)


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 6:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def analyze_message(message: str, previous_answer: str = "") -> MessageAnalysis:
    """Score frustration and detect a request to speak with a human."""

    # --- wants_human ---
    wants_human = bool(_HUMAN_RE.search(message))
    if not wants_human and _AGREEMENT_RE.match(message) and _ESCALATION_OFFER in (previous_answer or ""):
        wants_human = True

    # --- frustration (1–5) ---
    score = 1

    neg_hits = len(_FRUSTRATION_RE.findall(message))
    if neg_hits >= 3:
        score += 2
    elif neg_hits >= 1:
        score += 1

    if _caps_ratio(message) > 0.6 and len(message) > 10:
        score += 1

    exclamations = message.count("!")
    if exclamations >= 3 or exclamations >= 1 and neg_hits >= 1:
        score += 1

    return MessageAnalysis(frustration=min(score, 5), wants_human=wants_human)
