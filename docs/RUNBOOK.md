# Runbook

Operational procedures for running this service day-to-day.

## Health check

```
GET /health   → { "status": "ok", "version": "1.0.0" }
```
No auth required. Point uptime monitoring here.

## Common incidents

### The bot always replies "I don't have enough information"

Likely cause: retrieval is failing or the knowledge base is empty/stale.

1. Check backend logs for `Retrieval failed: ... — returning empty context.`
   (from `rag.py`'s `retrieve` node) — this means the Supabase RPC call or
   the Gemini embedding call is erroring, not that there's truly no match.
2. Check `RAG_MATCH_THRESHOLD` — if raised too high, real matches get filtered out.
3. Confirm `documents` table isn't empty: run
   `select count(*) from documents;` in the Supabase SQL editor.
4. If the knowledge base source changed recently, check the sync loop ran:
   look for `"Google Doc changed"` / `"Sync complete"` log lines, or
   trigger `POST /ingest` manually.

### 500s on `/chat`

1. Check backend logs (or Sentry, if `SENTRY_DSN` is set) for the
   `Unhandled error in /chat` traceback.
2. Common causes: Gemini quota exhausted (`ResourceExhausted` — handled
   gracefully in `rag.py`'s `generate`, so a raw 500 means something else),
   Supabase outage/auth failure, or a malformed environment variable.
3. Check `GET /health` — if that's also failing, it's likely
   Supabase/network connectivity, not app logic.

### High rate of automatic escalations

1. Query recent rows in `escalations`, group by `reason`.
2. `negative_sentiment` spikes → check for a genuine product issue or an
   incident affecting users, not just noisy sentiment keywords.
3. `repeated_unanswered` spikes → knowledge base gap; check
   `message_feedback` for low ratings on the same topic and treat it as a
   docs-content bug, not a code bug.

### Escalation emails aren't arriving

1. Check `EMAIL_BACKEND` — if `console` (the default), emails are only
   logged, never sent. Set `EMAIL_BACKEND=smtp` and the `SMTP_*` vars for
   real delivery.
2. If `smtp` is set: check logs for `EMAIL_BACKEND=smtp but
   ESCALATION_EMAIL_TO is not set` or an SMTP auth error from `notify.py`.

### Ingestion stuck / `/ingest` returns 409

`Ingestion already in progress.` — the in-memory `_ingest_lock` thinks a
run is active. This only clears on process restart if the background task
crashed without releasing the lock (see the `finally` block in `main.py`'s
`ingest` endpoint, which should always release it — if you hit this,
something raised outside that lifecycle). Restart the API process to clear
it, then check ingestion logs for the actual failure.

## Backups

Database backups are managed by Supabase (Settings → Database → Backups on
the Supabase dashboard — daily backups on paid tiers, retention depends on
plan). This repo does not run its own backup job. Before any destructive
schema change, take a manual backup/export from that dashboard first.

## Restore procedure

1. Supabase dashboard → Database → Backups → select a restore point.
2. Supabase restores to a new project or in-place, per their current UI —
   follow their guided flow.
3. After restore, verify: `select count(*) from documents;`,
   `select count(*) from chat_history;`, and a live `/chat` smoke test.

## Rotating the API key

1. Generate a new value for `API_KEY`.
2. Update it in DO App Platform env vars for the **backend** component.
3. Update `VITE_API_KEY` (or the host application's proxy env var — see
   `INTEGRATION.md`) for the **frontend**/consuming application(s).
4. Deploy both. There is a brief window of mismatch between steps 2 and 3
   where requests will 401 — schedule during low traffic if possible.

## Scaling beyond a single worker

The rate limiter and the ingest lock are in-memory and **only correct with
a single worker process** (enforced today by `--workers 1` in the
Dockerfile). Before increasing workers/replicas:
1. Replace `_session_hits` (main.py) and `_ingest_lock` with a shared store
   (Redis, or a Supabase table with a unique constraint).
2. Only then remove the `--workers 1` constraint.
