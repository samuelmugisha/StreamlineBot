"""FastAPI application entry point."""

import os
import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Security, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from .chat import handle_chat
from .memory import get_raw_history, save_feedback
from .sync import start_sync_loop
from .escalation import escalate
from .tickets import submit_ticket
from .schemas import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    HistoryMessage,
    IngestResponse,
    HealthResponse,
    EscalateRequest,
    EscalateResponse,
    FeedbackRequest,
    FeedbackResponse,
    TicketRequest,
    TicketResponse,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGSMITH_PROJECT", "Adminiebot")
os.environ.setdefault("LANGCHAIN_PROJECT", "Adminiebot")

# ─── Required environment variables ──────────────────────────────────────────

_REQUIRED_VARS = ["GOOGLE_AI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]

# ─── Rate limiting ────────────────────────────────────────────────────────────

_RATE_LIMIT = os.environ.get("RATE_LIMIT", "20/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[_RATE_LIMIT])

# /chat is the most expensive endpoint — retrieval + generation + sentiment
# scoring means multiple OpenAI calls per request — so it gets its own,
# stricter per-IP limit instead of sharing _RATE_LIMIT with /escalate and /feedback.
_CHAT_RATE_LIMIT = os.environ.get("CHAT_RATE_LIMIT", "8/minute")

# Per-conversation limit on /chat, independent of IP — catches abuse that
# rotates IPs but reuses a single session_id. In-memory only: resets on
# restart and assumes a single worker process (see _ingest_lock note below
# for the same single-worker requirement).
_SESSION_CHAT_LIMIT  = int(os.environ.get("SESSION_CHAT_LIMIT", 10))
_SESSION_CHAT_WINDOW = 60  # seconds

_session_hits: dict[str, list[float]] = {}
_session_hits_lock = threading.Lock()

# Star ratings at or below this value trigger an automatic Smart Agent Handoff.
_LOW_RATING_THRESHOLD = int(os.environ.get("LOW_RATING_ESCALATION_THRESHOLD", 3))


def _check_session_rate_limit(session_id: str) -> None:
    now = time.monotonic()
    with _session_hits_lock:
        # Sweep sessions with no recent activity to prevent unbounded dict growth
        if len(_session_hits) > 500:
            stale = [sid for sid, ts_list in _session_hits.items()
                     if not any(now - t < _SESSION_CHAT_WINDOW for t in ts_list)]
            for sid in stale:
                del _session_hits[sid]

        hits = [t for t in _session_hits.get(session_id, []) if now - t < _SESSION_CHAT_WINDOW]
        if len(hits) >= _SESSION_CHAT_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many messages in this conversation. Please wait a moment and try again.",
            )
        hits.append(now)
        _session_hits[session_id] = hits

# ─── API key auth ─────────────────────────────────────────────────────────────

_API_KEY = os.environ.get("API_KEY", "")

if not _API_KEY:
    logger.warning("API_KEY is not set — all endpoints are publicly accessible.")

def require_api_key(key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not _API_KEY:
        return
    if key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

# ─── Ingest lock ──────────────────────────────────────────────────────────────
# NOTE: This in-memory lock only works when the server runs with a single
# worker process (--workers 1). Multi-worker deployments require a
# distributed lock (e.g. Redis or a database row). The Docker CMD enforces
# single-worker mode to keep this safe.

_ingest_lock = threading.Lock()
_ingesting   = False

# ─── App ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [v for v in _REQUIRED_VARS if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values."
        )
    logger.info("AdminIE API starting...")
    app.state.sync_task = await start_sync_loop()
    yield
    app.state.sync_task.cancel()
    logger.info("AdminIE API shutting down.")


app = FastAPI(
    title="AdminIE AI Assistant API",
    version="1.0.0",
    description="RAG chatbot backend for AdminIE grant management system",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost,http://localhost:80,http://localhost:5173"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(_CHAT_RATE_LIMIT)
def chat(request: Request, body: ChatRequest):
    _check_session_rate_limit(body.session_id)
    try:
        return handle_chat(body)
    except Exception:
        logger.exception("Unhandled error in /chat")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@app.post("/escalate", response_model=EscalateResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(_RATE_LIMIT)
def escalate_chat(request: Request, body: EscalateRequest):
    try:
        escalate(body.session_id, reason="manual")
        return EscalateResponse(status="ok", detail="Our support team has been notified.")
    except Exception:
        logger.exception("Unhandled error in /escalate")
        raise HTTPException(status_code=500, detail="Could not escalate. Please try again.")


@app.post("/feedback", response_model=FeedbackResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(_RATE_LIMIT)
def feedback(request: Request, body: FeedbackRequest):
    try:
        save_feedback(
            session_id=body.session_id,
            question=body.question,
            answer=body.answer,
            rating=body.rating,
            comment=body.comment,
        )
        escalated = False
        if body.rating <= _LOW_RATING_THRESHOLD:
            escalate(body.session_id, reason="low_rating", extra_context=body.comment)
            escalated = True
        return FeedbackResponse(status="ok", escalated=escalated)
    except Exception:
        logger.exception("Unhandled error in /feedback")
        raise HTTPException(status_code=500, detail="Could not save feedback. Please try again.")


@app.get("/history/{session_id}", response_model=HistoryResponse, dependencies=[Depends(require_api_key)])
# NOTE: no per-user ownership check — any holder of the API key can read any session's history.
# For now session_ids are UUIDs (hard to guess). Proper fix: signed session tokens or user JWTs.
def history(session_id: str):
    try:
        raw = get_raw_history(session_id)
        messages = [HistoryMessage(role=m["type"], content=m["content"]) for m in raw]
        return HistoryResponse(session_id=session_id, messages=messages)
    except Exception:
        logger.exception("Unhandled error in /history")
        raise HTTPException(status_code=500, detail="Could not retrieve history. Please try again.")


@app.post("/ticket", response_model=TicketResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(_RATE_LIMIT)
def ticket(request: Request, body: TicketRequest):
    try:
        ticket_id = submit_ticket(
            name=body.name,
            email=body.email,
            module=body.module,
            subject=body.subject,
            description=body.description,
            priority=body.priority,
            session_id=body.session_id,
        )
        return TicketResponse(status="ok", ticket_id=ticket_id)
    except Exception:
        logger.exception("Unhandled error in /ticket")
        raise HTTPException(status_code=500, detail="Could not submit ticket. Please try again.")


@app.post("/ingest", response_model=IngestResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(_RATE_LIMIT)
def ingest(request: Request, background_tasks: BackgroundTasks, clear: bool = False):
    global _ingesting
    with _ingest_lock:
        if _ingesting:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ingestion already in progress. Please wait for it to finish.",
            )
        _ingesting = True

    def _run_and_release(clear_existing: bool) -> None:
        global _ingesting
        try:
            from backend.ingestion.ingest import ingest as run_ingest
            run_ingest(clear_existing=clear_existing)
        except Exception:
            logger.exception("Ingestion pipeline error")
        finally:
            with _ingest_lock:
                _ingesting = False

    try:
        background_tasks.add_task(_run_and_release, clear)
    except Exception:
        with _ingest_lock:
            _ingesting = False
        raise
    return IngestResponse(
        status="accepted",
        detail="Ingestion started in background. Monitor LangSmith for progress.",
    )
