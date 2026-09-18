"""Pydantic request / response schemas for the FastAPI endpoints."""

import uuid

from pydantic import BaseModel, Field, field_validator


def _require_uuid(v: str) -> str:
    try:
        uuid.UUID(v)
    except ValueError as e:
        raise ValueError("session_id must be a valid UUID v4 string") from e
    return v


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="UUID identifying the user session")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")

    _validate_session_id = field_validator("session_id")(_require_uuid)


class TutorialRef(BaseModel):
    module: str | None = None
    page: int | None = None
    image_url: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    escalated: bool = False
    tutorial: TutorialRef | None = None


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]


class EscalateRequest(BaseModel):
    session_id: str = Field(..., description="UUID identifying the user session")

    _validate_session_id = field_validator("session_id")(_require_uuid)


class EscalateResponse(BaseModel):
    status: str
    detail: str


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., description="UUID identifying the user session")
    question: str = Field(..., min_length=1, max_length=2000, description="The user message being rated")
    answer: str = Field(..., min_length=1, max_length=4000, description="AdminIE's reply being rated")
    rating: int = Field(..., ge=1, le=5, description="Star rating, 1 (not helpful) to 5 (very helpful)")
    comment: str | None = Field(None, max_length=1000, description="Optional follow-up comment")

    _validate_session_id = field_validator("session_id")(_require_uuid)


class FeedbackResponse(BaseModel):
    status: str
    escalated: bool = False


class TicketRequest(BaseModel):
    session_id: str | None = Field(None, description="Chat session that triggered the ticket")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=200)
    module: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=300)
    description: str = Field(..., min_length=1, max_length=5000)
    priority: str = Field(default="Medium", pattern="^(Low|Medium|Urgent)$")


class TicketResponse(BaseModel):
    status: str
    ticket_id: str


class IngestResponse(BaseModel):
    status: str
    detail: str


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
