# AdminIE AI Support Assistant

An AI-powered RAG chatbot embedded as a floating widget on the AdminIE Grant Management System. AdminIE answers questions about AdminIE software modules using verified documentation, maintains per-user conversation memory, and escalates to human support when needed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini (`gemini-2.0-flash` by default, see `GEMINI_MODEL`) |
| Embeddings | Google `gemini-embedding-001` |
| Vector Store | Supabase pgvector |
| Orchestration | LangGraph |
| Memory | Supabase `chat_history` table (per session) |
| Backend | FastAPI (Python 3.12) |
| Frontend | React + Vite + Tailwind CSS |
| Monitoring | LangSmith (tracing) + optional Sentry (errors) |
| Testing | pytest (backend), Vitest + React Testing Library (frontend) |
| CI/CD | GitHub Actions |
| Deployment | Docker + DigitalOcean App Platform |

---

## Project Structure

```
adminIEBot/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app — routes, CORS, API key auth, rate limiting
│   │   ├── chat.py        # Chat handler — wires memory + RAG + escalation
│   │   ├── rag.py         # LangGraph RAG agent (retrieve → generate)
│   │   ├── memory.py      # Chat history read/write via Supabase
│   │   ├── sentiment.py   # Frustration scoring + "wants human" detection
│   │   ├── escalation.py  # Smart Agent Handoff — escalate to a human
│   │   ├── notify.py      # Escalation email delivery (console / SMTP)
│   │   ├── tutorials.py   # Tutorial image URL/path helpers (Supabase Storage)
│   │   └── schemas.py     # Pydantic request/response models
│   ├── ingestion/
│   │   ├── ingest.py                  # PDF OCR pipeline (GPT-4o-mini Vision → pgvector)
│   │   └── export_tutorial_images.py  # One-time export of PDF pages to Supabase Storage
│   ├── db/
│   │   └── schema.sql     # Supabase table definitions + match_documents()
│   └── data/              # Source PDF knowledge base (8 modules)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Widget shell — session, preview bubble, toggle
│   │   ├── main.jsx                   # React entry point
│   │   ├── index.css                  # Tailwind + scrollbar styles
│   │   └── components/
│   │       ├── ChatWindow.jsx         # Chat UI — history, send, new chat
│   │       ├── MessageBubble.jsx      # Individual message bubble
│   │       ├── TypingIndicator.jsx    # Animated loading dots
│   │       ├── BotAvatar.jsx          # SVG robot avatar
│   │       └── ErrorBoundary.jsx      # Widget crash fallback
│   ├── Dockerfile                     # nginx multi-stage build
│   ├── .env.example                   # Frontend env vars template
│   └── .gitignore
├── Dockerfile                         # Backend API container
├── docker-compose.yml                 # Orchestrates api + widget services
├── .dockerignore                      # Keeps secrets + data out of images
├── .env.example                       # Backend env vars template
├── requirements.txt                   # Python dependencies
└── plan.md                            # Full project plan and timeline
```

---

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd adminIEBot
cp .env.example .env
# Fill in all values in .env
```

### 2. Supabase — run schema

For a **fresh** Supabase project, run `backend/db/schema.sql` in the SQL Editor.
This creates the `documents`, `chat_history`, and `escalations` tables and the
`match_documents` function. Then also run `backend/db/migration_feedback.sql`
to add the `message_feedback` table.

 **Do not re-run the full script on an existing project** — it starts with
`drop table if exists documents cascade`, which would wipe your embedded
knowledge base. If you already have `documents` and `chat_history`, instead
run the targeted migration files (`migration_handoff_sentiment.sql`,
`migration_feedback.sql`) to add the new tables/columns.

### 3. Backend

```bash
# Create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt

# Run the ingestion pipeline (one-time — OCRs all PDFs into Supabase)
python -m backend.ingestion.ingest

# If ingestion was interrupted after OCR, resume with:
python -m backend.ingestion.ingest --embed-only

# Start the API server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend

```bash
cd frontend
cp .env.example .env    # set VITE_API_URL and VITE_API_KEY
npm install
npm run dev             # http://localhost:5173
```

---

## Testing & Code Quality

```bash
# Backend — from the repo root
pip install -r requirements-dev.txt
ruff check backend Tests      # lint
ruff format --check backend Tests   # format check
pytest                        # tests + coverage report

# Frontend — from frontend/
npm run lint
npm run format:check
npm run test
```

CI runs all of the above automatically on every push/PR — see
`.github/workflows/ci.yml`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
full workflow and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the
pieces fit together.

---

## Deployed URL

The chatbot is live at:

**https://coral-app-cwkpt.ondigitalocean.app**

The backend API is served under the `/api` prefix:

| Environment | Base URL |
|---|---|
| Production | `https://coral-app-cwkpt.ondigitalocean.app/api` |
| Local dev | `http://localhost:8001` |

---

## API Endpoints

All endpoints except `/health` require the `Authorization: Bearer <API_KEY>` header in production.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Send a message, get a response |
| `POST` | `/escalate` | Hand off the conversation to a human agent |
| `POST` | `/feedback` | Rate a bot answer (1-5 stars), optionally with a comment |
| `GET` | `/history/{session_id}` | Retrieve conversation history |
| `POST` | `/ingest` | Trigger PDF re-ingestion (background) |

Interactive docs available at `http://localhost:8001/docs` (local) or `https://coral-app-cwkpt.ondigitalocean.app/api/docs` (production).

### POST /chat

```json
// Request
{ "session_id": "550e8400-e29b-41d4-a716-446655440000", "message": "How do I add a new deal?" }

// Response
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "To add a new deal...",
  "escalated": false,
  "tutorial": {
    "module": "Crm",
    "page": 8,
    "image_url": "https://<project>.supabase.co/storage/v1/object/public/tutorials/Crm/CRM_module/page-8.png"
  }
}
```

`escalated` is `true` when the bot automatically handed the conversation off to
a human (see Smart Agent Handoff below).

`tutorial` is `null` when the bot's answer wasn't based on a specific PDF page
(e.g. the bot couldn't answer, or the match came from the Google Doc KB).
Otherwise it points to a screenshot of the source PDF page (see Tutorial
Visuals below).

### POST /escalate

```json
// Request
{ "session_id": "550e8400-e29b-41d4-a716-446655440000" }

// Response
{ "status": "ok", "detail": "Our support team has been notified." }
```

### POST /feedback

```json
// Request
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "How do I add a new deal?",
  "answer": "To add a new deal...",
  "rating": 2,
  "comment": "Didn't explain where to find the button"
}

// Response
{ "status": "ok", "escalated": true }
```

`comment` is optional. `escalated` is `true` when the rating is at or below
`LOW_RATING_ESCALATION_THRESHOLD` (default `3`), which also triggers a Smart
Agent Handoff (reason `low_rating`).

---

## Smart Agent Handoff & Sentiment Analysis

Every user message is analyzed by `sentiment.py`, which scores frustration
(1–5, stored in `chat_history.sentiment`) and detects whether the user is
asking to speak with a human. A conversation is automatically escalated —
saved to the `escalations` table and emailed to support — when:

- the user explicitly asks for a human/support (directly, or by agreeing to
  the bot's offer to forward them — e.g. "yes please" after the bot offers
  to notify support),
- the frustration score reaches `SENTIMENT_ESCALATION_THRESHOLD` (default `4`), or
- the bot replies with "I don't have enough information" `NO_ANSWER_STREAK_THRESHOLD`
  times in a row (default `2`), or
- the user rates a reply `LOW_RATING_ESCALATION_THRESHOLD` stars or below
  (default `3`) via the "Was this helpful?" prompt (see Feedback below).

When the bot can't answer, it now also proactively offers to notify support,
so a follow-up like "yes please" triggers the handoff above.

Users can also trigger a handoff manually via the "Get Help" button in
the widget header, which calls `POST /escalate`.

---

## Feedback ("Was this helpful?")

Every bot reply shows a 1-5 star rating prompt. Ratings are saved to the
`message_feedback` table (question, answer, rating, optional comment) via
`POST /feedback`.

- **4-5 stars** — saved silently, no further action.
- **1-3 stars** — the widget asks an optional follow-up ("what could I have
  done better?"), then saves the rating + comment and automatically triggers
  a Smart Agent Handoff (reason `low_rating`), notifying support the same way
  as the sentiment-based escalations above.

Low-rated exchanges are a useful queue for AdminIE staff to review for
knowledge-base gaps — recurring low ratings on a topic signal that the
underlying documentation needs improvement.

**Email delivery** is controlled by `EMAIL_BACKEND`:
- `console` (default) — logs the escalation email instead of sending it. Use
  this until AdminIE provides SMTP credentials.
- `smtp` — sends via `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD`
  to `ESCALATION_EMAIL_TO`.

---

## Tutorial Visuals

Each `/chat` response includes a `tutorial` field pointing to a screenshot of
the PDF page the answer was drawn from. The widget shows a "📷 View tutorial"
link under the answer, opening the image in a new tab.

How it works:
- `backend/ingestion/export_tutorial_images.py` is a one-time script that
  renders every page of every PDF in `backend/data/` to a PNG (150 DPI) and
  uploads them to the public Supabase Storage bucket `tutorials`, mirroring
  each PDF's folder structure (e.g. `Crm/CRM_module/page-8.png`).
- `backend/app/tutorials.py` derives the image URL from the `source`/`page`
  fields already present in each PDF chunk's `documents.metadata` — no extra
  ingestion or DB columns needed.
- `rag.py`'s `retrieve` step attaches the top-matched chunk's tutorial info to
  the graph state; `chat.py` suppresses it when the bot couldn't answer.
- Google Doc KB chunks have no `page` metadata, so they never produce a
  tutorial link.

Re-run the export script after adding/changing PDFs in `backend/data/`:
```bash
python -m backend.ingestion.export_tutorial_images
```

---

## Embedding in the Grant Management System

### 1. Build the widget

```bash
cd frontend
npm run build   # outputs to frontend/dist/
```

Upload `frontend/dist/` to your CDN or static hosting.

### 2. Add the snippet to your grants system HTML

Place this before `</body>`, replacing the placeholder values with real ones:

```html
<!-- AdminIE widget mount point -->
<div id="root"></div>

<!-- Runtime config — set BEFORE loading the widget script -->
<script>
  window.ADMINIE_SESSION_ID = "{{ current_user.id }}";        // logged-in user's ID
  window.ADMINIE_API_URL    = "https://your-api-domain.com";  // your deployed API URL
  window.ADMINIE_API_KEY    = "your-production-api-key";      // must match API_KEY in .env
</script>

<!-- Widget bundle -->
<script type="module" src="https://your-cdn.com/assets/index.js"></script>
<link rel="stylesheet" href="https://your-cdn.com/assets/index.css">
```

The widget reads `window.ADMINIE_*` at runtime — this is how the grants system passes the
logged-in user's ID so each user gets their own isolated conversation history.

### 3. Production security — backend proxy (recommended)

Do **not** call the AdminIE API directly from the browser. The API key would be visible
in DevTools to any user. Instead, have the grants system backend proxy the request:

```
Browser → Adminie backend → (Authorization: Bearer <key>) → AdminIE API
```

**Example proxy endpoint (Node/Express):**

```js
app.post('/chatbot/message', requireAuth, async (req, res) => {
  const { message, session_id } = req.body;
  const response = await fetch('https://coral-app-cwkpt.ondigitalocean.app/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.ADMINIE_API_KEY}`,
    },
    body: JSON.stringify({ message, session_id }),
  });
  const data = await response.json();
  res.json(data);
});
```

Store `ADMINIE_API_KEY` in the adminie backend's environment variables — it never reaches
the browser. The API key will be provided separately by the AdminIE team.

---

## Knowledge Base

The chatbot is trained on 8 AdminIE PDF modules:

| Module | File |
|---|---|
| CRM | `backend/data/Crm/CRM_module.pdf` |
| Finance | `backend/data/Finance/finance_module.pdf` |
| HR | `backend/data/hr/humanResourceModule.pdf` |
| Banking | `backend/data/banking/banking_module.pdf` |
| Policies | `backend/data/policies/PoliciesModule.pdf` |
| Programs | `backend/data/Programs/programs_module.pdf` |
| Projects | `backend/data/Projects/project_guide.pdf` |
| Q&A | `backend/data/Questions/Questions-adminie.pdf` |

To add new documents, drop PDFs into the appropriate folder and run:
```bash
python -m backend.ingestion.ingest --clear
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `API_KEY` | Secret key for API authentication (leave blank to disable in dev) |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins |
| `RATE_LIMIT` | Max requests per IP per minute on `/escalate` and `/feedback` (default: `20/minute`) |
| `CHAT_RATE_LIMIT` | Max requests per IP per minute on `/chat` (default: `8/minute`) |
| `SESSION_CHAT_LIMIT` | Max `/chat` requests per conversation per 60s, independent of IP (default: `10`) |
| `GOOGLE_AI_API_KEY` | Google AI (Gemini) API key |
| `GEMINI_MODEL` | Chat model name (default: `gemini-2.0-flash`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side only) |
| `LANGSMITH_API_KEY` | LangSmith API key for monitoring |
| `LANGSMITH_PROJECT` | LangSmith project name |
| `EMAIL_BACKEND` | `console` (log only) or `smtp` (send escalation emails) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP credentials (required when `EMAIL_BACKEND=smtp`) |
| `ESCALATION_EMAIL_TO` | Recipient for escalation emails |
| `SENTIMENT_ESCALATION_THRESHOLD` | Frustration score (1-5) that auto-escalates (default: `4`) |
| `NO_ANSWER_STREAK_THRESHOLD` | Consecutive unanswered replies before auto-escalating (default: `2`) |
| `LOW_RATING_ESCALATION_THRESHOLD` | "Was this helpful?" star rating (1-5) at or below which auto-escalates (default: `3`) |
| `SENTRY_DSN` / `VITE_SENTRY_DSN` | Optional error tracking (leave blank to disable) |

---

## Support

If AdminIE cannot answer your question, contact the AdminIE team:
- success@adminie.com
- founders@adminie.com
