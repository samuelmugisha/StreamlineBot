# Changelog

All notable changes to this project are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Backend test suite (pytest) covering sentiment analysis, schema
  validation, chat/escalation logic, and all API endpoints — 54 tests.
- Frontend test suite (Vitest + React Testing Library) covering the widget,
  chat window, feedback, ticket form, and error boundary.
- CI pipeline (GitHub Actions): lint, format check, tests, dependency
  vulnerability scanning, and Docker build verification on every push/PR.
- CD pipeline: builds and publishes versioned Docker images to GHCR on
  merge to `main`, with an optional DigitalOcean App Platform deploy trigger.
- CodeQL static analysis (weekly + on every PR) and Dependabot for pip,
  npm, Docker, and GitHub Actions.
- Security response headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`) on every backend response.
- Optional Sentry error tracking for backend and frontend (opt-in via
  `SENTRY_DSN` / `VITE_SENTRY_DSN`).
- Accessible labels (`aria-label`) on previously icon-only buttons in the
  chat widget (send, close, new conversation).
- Repo hygiene: `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
  `.editorconfig`, PR/issue templates, `CODEOWNERS`.
- `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/RUNBOOK.md`.
- Ruff (lint + format) for the backend; ESLint + Prettier for the frontend.

### Fixed
- `backend/ingestion/gdoc_ingest.py`: `Path` was used without being
  imported, which would raise `NameError` the first time local dev fell
  back to `GOOGLE_CREDENTIALS_FILE` instead of `GOOGLE_CREDENTIALS_JSON`.
- Deduplicated three copies of the same `session_id` UUID validator across
  `backend/app/schemas.py` into one shared validator.
- Removed unused `Security`/`APIKeyHeader` imports in `backend/app/main.py`.
- Bumped `fastapi`, `python-multipart`, `python-dotenv`, `Pillow`, and
  `requests` to versions patched against known CVEs (see `pip-audit` output
  in CI). The LangChain/LangGraph stack has open advisories too, but their
  fixes are major-version jumps with breaking API changes — deliberately
  left for a dedicated, tested upgrade rather than bundled in here.

### Changed
- README updated to describe the actual stack (Gemini, not OpenAI) and to
  document testing/CI.
