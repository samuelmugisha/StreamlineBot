"""Integration tests for the FastAPI HTTP layer in backend.app.main.

Route handlers (handle_chat, escalate, save_feedback, submit_ticket,
get_raw_history) are monkeypatched at the backend.app.main module level so
these tests exercise routing, auth, validation, and error handling without
any real Supabase/Gemini/SMTP calls.
"""

import uuid

from backend.app import main as main_module

VALID_UUID = str(uuid.uuid4())


def test_health_returns_ok_without_auth(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "version": "1.0.0"}


def test_chat_requires_api_key(client):
    res = client.post("/chat", json={"session_id": VALID_UUID, "message": "hi"})
    assert res.status_code == 401


def test_chat_rejects_wrong_api_key(client):
    res = client.post(
        "/chat",
        json={"session_id": VALID_UUID, "message": "hi"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert res.status_code == 401


def test_chat_succeeds_with_valid_key(client, auth_headers, monkeypatch):
    from backend.app.schemas import ChatResponse

    monkeypatch.setattr(
        main_module,
        "handle_chat",
        lambda body: ChatResponse(session_id=body.session_id, answer="Here's how...", escalated=False),
    )
    res = client.post(
        "/chat",
        json={"session_id": VALID_UUID, "message": "How do I add a deal?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["answer"] == "Here's how..."


def test_chat_rejects_invalid_session_id(client, auth_headers):
    res = client.post(
        "/chat",
        json={"session_id": "not-a-uuid", "message": "hi"},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_chat_rejects_empty_message(client, auth_headers):
    res = client.post(
        "/chat",
        json={"session_id": VALID_UUID, "message": ""},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_chat_returns_500_on_unhandled_error_without_leaking_details(client, auth_headers, monkeypatch):
    def boom(body):
        raise RuntimeError("supabase connection string leaked here")

    monkeypatch.setattr(main_module, "handle_chat", boom)
    res = client.post(
        "/chat",
        json={"session_id": VALID_UUID, "message": "hi"},
        headers=auth_headers,
    )
    assert res.status_code == 500
    assert "supabase" not in res.json()["detail"].lower()


def test_escalate_endpoint(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main_module, "escalate", lambda session_id, reason, **k: None)
    res = client.post("/escalate", json={"session_id": VALID_UUID}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_feedback_low_rating_triggers_escalation(client, auth_headers, monkeypatch):
    escalate_calls = []
    monkeypatch.setattr(main_module, "save_feedback", lambda **k: None)
    monkeypatch.setattr(
        main_module, "escalate", lambda session_id, reason, **k: escalate_calls.append(reason)
    )
    res = client.post(
        "/feedback",
        json={"session_id": VALID_UUID, "question": "q", "answer": "a", "rating": 1},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["escalated"] is True
    assert escalate_calls == ["low_rating"]


def test_feedback_high_rating_does_not_escalate(client, auth_headers, monkeypatch):
    escalate_calls = []
    monkeypatch.setattr(main_module, "save_feedback", lambda **k: None)
    monkeypatch.setattr(
        main_module, "escalate", lambda session_id, reason, **k: escalate_calls.append(reason)
    )
    res = client.post(
        "/feedback",
        json={"session_id": VALID_UUID, "question": "q", "answer": "a", "rating": 5},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["escalated"] is False
    assert escalate_calls == []


def test_feedback_rejects_out_of_range_rating(client, auth_headers):
    res = client.post(
        "/feedback",
        json={"session_id": VALID_UUID, "question": "q", "answer": "a", "rating": 9},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_history_endpoint(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "get_raw_history",
        lambda session_id: [{"type": "human", "content": "hi"}, {"type": "ai", "content": "hello"}],
    )
    res = client.get(f"/history/{VALID_UUID}", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["messages"] == [
        {"role": "human", "content": "hi"},
        {"role": "ai", "content": "hello"},
    ]


def test_ticket_endpoint_creates_ticket(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main_module, "submit_ticket", lambda **k: "ticket-123")
    res = client.post(
        "/ticket",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "module": "Finance",
            "subject": "Cannot export report",
            "description": "The export button is greyed out.",
            "priority": "Urgent",
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "ticket_id": "ticket-123"}


def test_ticket_rejects_invalid_priority(client, auth_headers):
    res = client.post(
        "/ticket",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "module": "Finance",
            "subject": "x",
            "description": "x",
            "priority": "Critical",
        },
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_cors_rejects_disallowed_origin(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main_module, "escalate", lambda session_id, reason, **k: None)
    res = client.post(
        "/escalate",
        json={"session_id": VALID_UUID},
        headers={**auth_headers, "Origin": "https://evil.example.com"},
    )
    # FastAPI/Starlette still processes the request but omits CORS headers
    # for a disallowed origin — the browser is what enforces the block.
    assert "access-control-allow-origin" not in {k.lower() for k in res.headers}
