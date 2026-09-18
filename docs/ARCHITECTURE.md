# Architecture

## Overview

The Streamline AI Support Assistant is a RAG (Retrieval-Augmented
Generation) chatbot, shipped as an embeddable widget plus a backend API.
It answers questions about Streamline's software modules using ingested
product documentation, remembers per-session conversation history, and
escalates to a human when it can't help.

```
Browser (widget)
   │  X-API-Key
   ▼
FastAPI backend  ──────────────►  Google Gemini (chat + embeddings)
   │        │
   │        └────────────────►  Supabase (Postgres + pgvector + Storage)
   │
   └──────────────────────────►  Google Drive / Docs (source documentation)
```

## Components

### Frontend (`frontend/`)
A React + Vite + Tailwind single-page widget, built to a static bundle and
served by nginx (see `frontend/Dockerfile`). It mounts as a floating
button/chat window and is embedded into a host application via a `<script>`
tag (see `INTEGRATION.md`) — it is not a standalone site.

### Backend (`backend/app/`)
FastAPI application. Key modules:

| Module | Responsibility |
|---|---|
| `main.py` | Routes, CORS, security headers, API-key auth, rate limiting |
| `chat.py` | Orchestrates a single chat turn: greeting shortcut → RAG → sentiment → escalation |
| `rag.py` | LangGraph agent: `retrieve` (pgvector similarity search) → `generate` (Gemini chat completion) |
| `memory.py` | Reads/writes `chat_history` in Supabase |
| `sentiment.py` | Pure keyword-based frustration scoring + "wants human" detection (no LLM call) |
| `escalation.py` | Smart Agent Handoff — records the escalation and emails support |
| `tickets.py` | Support ticket submission |
| `sync.py` | Background loop that re-ingests the knowledge base when the source doc/folder changes |
| `tutorials.py` | Maps a matched document chunk to its tutorial screenshot URL |

### Ingestion (`backend/ingestion/`)
Offline/background pipelines that turn source documents (PDFs, a Google
Doc, a Google Drive folder) into embedded chunks in Supabase's `documents`
table. Not part of the request path — triggered manually, via `/ingest`, or
by the background sync loop in `sync.py`.

### Data (Supabase)
- `documents` — knowledge base chunks + `vector(1536)` embeddings (pgvector, RLS: public read, service-role write only)
- `chat_history` — per-session conversation log, with a `sentiment` score per human message
- `escalations` — full transcript captured at the moment of a Smart Agent Handoff
- `message_feedback` — 1-5 star ratings on bot replies
- `sync_state` — last-synced markers for the background ingestion loop

See `backend/db/schema.sql` and the `migration_*.sql` files for exact
definitions.

## Request flow: `POST /chat`

1. `require_api_key` dependency checks `X-API-Key` (skipped if `API_KEY` unset)
2. Per-IP and per-session rate limits are checked
3. `chat.handle_chat`:
   - Bare greetings ("hi", "hello") short-circuit with a canned reply — no RAG/LLM call
   - Otherwise `rag.run_rag` retrieves the top matching chunks from pgvector and asks Gemini to answer from that context
   - `sentiment.analyze_message` scores frustration and detects an explicit request for a human — pure regex/keyword logic, zero LLM calls
   - The turn is saved to `chat_history`
   - If frustration/streak/explicit-request thresholds are crossed, `escalation.escalate` fires (saves to `escalations`, emails support)
4. Response includes the answer, an `escalated` flag, and an optional `tutorial` image reference

## Why these choices

- **LangGraph for the RAG graph**: a two-node graph (`retrieve` → `generate`)
  is intentionally minimal — it's a place to add nodes (e.g. a rerank step,
  a query-rewrite step) without restructuring `chat.py`.
- **Sentiment analysis is keyword-based, not LLM-based**: keeps escalation
  detection fast and free of extra Gemini calls/quota, at the cost of being
  less nuanced than an LLM judge. See `sentiment.py`'s docstring.
- **In-memory rate limiting and ingest lock**: simple and sufficient for a
  single-worker deployment (enforced by the Dockerfile). Scaling to
  multiple workers requires moving both to a shared store (Redis, or a
  Supabase row) first — see `SECURITY.md`'s known limitations.
