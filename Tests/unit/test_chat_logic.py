"""Unit tests for backend.app.chat — greeting shortcut, no-answer streak, and
escalation routing. External calls (RAG, memory, escalation) are mocked so
these tests exercise only chat.py's own decision logic.
"""

from langchain_core.messages import AIMessage, HumanMessage

from backend.app import chat
from backend.app.escalation import NO_ANSWER_PHRASE
from backend.app.schemas import ChatRequest

VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _no_answer_reply():
    return (
        f"{NO_ANSWER_PHRASE} on that. I can notify our support team and have them "
        "follow up with you by email — just let me know if you'd like me to do that."
    )


class TestGreetingShortcut:
    def test_bare_greeting_skips_rag(self, monkeypatch):
        called = False

        def fake_run_rag(**kwargs):
            nonlocal called
            called = True
            return {"answer": "should not be used", "tutorial": None}

        monkeypatch.setattr(chat, "run_rag", fake_run_rag)
        monkeypatch.setattr(chat, "load_window", lambda *a, **k: [])
        monkeypatch.setattr(chat, "save_exchange", lambda **k: None)

        response = chat.handle_chat(ChatRequest(session_id=VALID_UUID, message="hello"))

        assert called is False
        assert "How can I help you today?" in response.answer
        assert response.tutorial is None

    def test_non_greeting_uses_rag(self, monkeypatch):
        monkeypatch.setattr(
            chat,
            "run_rag",
            lambda **k: {"answer": "Here's how...", "tutorial": {"module": "CRM", "image_url": "x"}},
        )
        monkeypatch.setattr(chat, "load_window", lambda *a, **k: [])
        monkeypatch.setattr(chat, "save_exchange", lambda **k: None)

        response = chat.handle_chat(ChatRequest(session_id=VALID_UUID, message="How do I add a deal?"))

        assert response.answer == "Here's how..."
        assert response.tutorial is not None


class TestNoAnswerSuppressesTutorial:
    def test_tutorial_dropped_when_bot_could_not_answer(self, monkeypatch):
        monkeypatch.setattr(
            chat,
            "run_rag",
            lambda **k: {"answer": _no_answer_reply(), "tutorial": {"module": "CRM", "image_url": "x"}},
        )
        monkeypatch.setattr(chat, "load_window", lambda *a, **k: [])
        monkeypatch.setattr(chat, "save_exchange", lambda **k: None)

        response = chat.handle_chat(ChatRequest(session_id=VALID_UUID, message="something obscure"))

        assert response.tutorial is None


class TestEscalationRouting:
    def _run(
        self, monkeypatch, message, answer="Here's how...", history=None, frustration=1, wants_human=False
    ):
        escalate_calls = []
        monkeypatch.setattr(chat, "run_rag", lambda **k: {"answer": answer, "tutorial": None})
        monkeypatch.setattr(chat, "load_window", lambda *a, **k: history or [])
        monkeypatch.setattr(chat, "save_exchange", lambda **k: None)
        monkeypatch.setattr(
            chat,
            "analyze_message",
            lambda *a, **k: type("A", (), {"frustration": frustration, "wants_human": wants_human})(),
        )
        monkeypatch.setattr(chat, "escalate", lambda session_id, reason, **k: escalate_calls.append(reason))
        response = chat.handle_chat(ChatRequest(session_id=VALID_UUID, message=message))
        return response, escalate_calls

    def test_wants_human_triggers_escalation(self, monkeypatch):
        response, calls = self._run(monkeypatch, "talk to a human", wants_human=True)
        assert response.escalated is True
        assert calls == ["user_requested_human"]

    def test_high_frustration_triggers_escalation(self, monkeypatch):
        response, calls = self._run(monkeypatch, "this is terrible", frustration=5)
        assert response.escalated is True
        assert calls == ["negative_sentiment"]

    def test_calm_answered_message_does_not_escalate(self, monkeypatch):
        response, calls = self._run(monkeypatch, "how do I export a report?")
        assert response.escalated is False
        assert calls == []

    def test_repeated_no_answer_streak_triggers_escalation(self, monkeypatch):
        history = [
            HumanMessage(content="a weird question"),
            AIMessage(content=_no_answer_reply()),
        ]
        response, calls = self._run(
            monkeypatch, "another weird question", answer=_no_answer_reply(), history=history
        )
        assert response.escalated is True
        assert calls == ["repeated_unanswered"]

    def test_single_no_answer_does_not_yet_escalate(self, monkeypatch):
        response, calls = self._run(monkeypatch, "a weird question", answer=_no_answer_reply(), history=[])
        assert response.escalated is False
        assert calls == []
