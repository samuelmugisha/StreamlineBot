"""Shared pytest fixtures.

Sets hermetic environment variables *before* backend.app.main (and its
transitive imports) are loaded, so importing the app never requires real
Google/Supabase credentials and never makes a network call. Rate limits are
raised to avoid flaky 429s when many tests exercise the same endpoint back
to back.
"""

import os

os.environ["GOOGLE_AI_API_KEY"] = "test-google-ai-key"
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["API_KEY"] = "test-api-key"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["RATE_LIMIT"] = "1000/minute"
os.environ["CHAT_RATE_LIMIT"] = "1000/minute"
os.environ["SESSION_CHAT_LIMIT"] = "1000"
os.environ["GDOC_SYNC_INTERVAL_MINUTES"] = "60"
os.environ["EMAIL_BACKEND"] = "console"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

API_KEY = os.environ["API_KEY"]
AUTH_HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client():
    """A TestClient that runs the app's lifespan (startup/shutdown) once per test."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return dict(AUTH_HEADERS)
