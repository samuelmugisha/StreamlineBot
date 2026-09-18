# Security Policy

This project (the Streamline AI Support Assistant) handles customer support
conversations and, indirectly, references to account/module data. Report
security issues privately — do not open a public GitHub issue.

## Reporting a vulnerability

Email **success@adminie.com** (or **founders@adminie.com**) with:

- A description of the issue and its potential impact
- Steps to reproduce (or a proof of concept)
- Any relevant logs, request/response samples, or affected endpoint(s)

We aim to acknowledge reports within 3 business days. Please give us a
reasonable window to fix an issue before public disclosure.

## Supported versions

Only the `main` branch and the currently deployed production instance are
supported. There is no long-term-support branch.

## What's in scope

- The FastAPI backend (`backend/`)
- The chat widget frontend (`frontend/`)
- CI/CD configuration (`.github/workflows/`)
- Infrastructure config committed to this repo (`Dockerfile`, `docker-compose.yml`)

## Security measures already in place

- **Authentication**: all endpoints except `/health` require the `X-API-Key`
  header (`API_KEY` env var). See `backend/app/main.py`.
- **Rate limiting**: per-IP limits on every endpoint, plus a stricter
  per-conversation limit on `/chat` independent of IP.
- **Input validation**: all request bodies are validated with Pydantic
  (length limits, UUID format, enum-constrained fields).
- **CORS**: restricted to an explicit `ALLOWED_ORIGINS` allowlist.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy` are set on every response.
- **Secrets**: never committed — `.env`, `backend/credentials/`, and
  `.env.streamline` are gitignored. `.env.example` documents required
  variables with placeholder values only.
- **Row Level Security**: Supabase `documents` table has RLS enabled
  (public read, service-role-only write). See `backend/db/schema.sql` for
  the current RLS posture and its documented limitations for `chat_history`.
- **Dependency scanning**: `pip-audit` (Python) and `npm audit` (frontend)
  run in CI on every push; CodeQL static analysis runs weekly and on every
  PR. Dependabot opens weekly update PRs for pip, npm, Docker base images,
  and GitHub Actions.
- **Error tracking**: optional Sentry integration (`SENTRY_DSN`). Disabled
  by default — no data is sent anywhere until a DSN is configured.
  `send_default_pii` is explicitly disabled on both backend and frontend, so
  Sentry does not automatically collect request bodies, user IPs, or cookies.

## Known limitations (tracked, not hidden)

- `chat_history` does not have per-user Row Level Security — the backend
  uses the Supabase service-role key, which bypasses RLS by design. Session
  isolation is enforced at the API layer (API key + cryptographically random
  session UUIDs). See the note in `backend/db/schema.sql` for the migration
  path to full RLS via Supabase Auth.
- The in-memory rate limiter and ingest lock require the API to run as a
  single worker process (already enforced in the Dockerfile's `CMD`). A
  multi-worker deployment needs a distributed lock (Redis or a DB row)
  first.
- If the widget's API key is embedded directly in a browser bundle (rather
  than proxied through the host application's backend), it is visible in
  DevTools to any user of that page. See `INTEGRATION.md` for the
  recommended backend-proxy pattern.
