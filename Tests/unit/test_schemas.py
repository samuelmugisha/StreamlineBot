"""Unit tests for Pydantic request/response validation in backend.app.schemas."""

import uuid

import pytest
from pydantic import ValidationError

from backend.app.schemas import ChatRequest, FeedbackRequest, TicketRequest

VALID_UUID = str(uuid.uuid4())


def test_chat_request_accepts_valid_uuid_and_message():
    req = ChatRequest(session_id=VALID_UUID, message="How do I add a new deal?")
    assert req.session_id == VALID_UUID


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "", "12345", "'; DROP TABLE users; --"])
def test_chat_request_rejects_invalid_session_id(bad_id):
    with pytest.raises(ValidationError):
        ChatRequest(session_id=bad_id, message="hello")


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(session_id=VALID_UUID, message="")


def test_chat_request_rejects_overlong_message():
    with pytest.raises(ValidationError):
        ChatRequest(session_id=VALID_UUID, message="a" * 2001)


def test_feedback_request_rejects_out_of_range_rating():
    with pytest.raises(ValidationError):
        FeedbackRequest(session_id=VALID_UUID, question="q", answer="a", rating=6)


def test_feedback_request_rejects_zero_rating():
    with pytest.raises(ValidationError):
        FeedbackRequest(session_id=VALID_UUID, question="q", answer="a", rating=0)


def test_feedback_request_accepts_boundary_ratings():
    for rating in (1, 5):
        req = FeedbackRequest(session_id=VALID_UUID, question="q", answer="a", rating=rating)
        assert req.rating == rating


def test_ticket_request_requires_valid_priority():
    with pytest.raises(ValidationError):
        TicketRequest(
            name="Jane",
            email="jane@example.com",
            module="Finance",
            subject="Cannot export report",
            description="The export button is greyed out.",
            priority="Critical",  # not one of Low/Medium/Urgent
        )


def test_ticket_request_defaults_priority_to_medium():
    req = TicketRequest(
        name="Jane",
        email="jane@example.com",
        module="Finance",
        subject="Cannot export report",
        description="The export button is greyed out.",
    )
    assert req.priority == "Medium"


def test_ticket_request_rejects_empty_required_fields():
    with pytest.raises(ValidationError):
        TicketRequest(name="", email="jane@example.com", module="Finance", subject="x", description="x")
