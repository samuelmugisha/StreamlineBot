"""Ticket submission — stores in Supabase; add Samuel's webhook here when ready."""

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase: Client | None = None


def _get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _supabase


def submit_ticket(
    name: str,
    email: str,
    module: str,
    subject: str,
    description: str,
    priority: str,
    session_id: str | None = None,
) -> str:
    sb = _get_supabase()
    result = (
        sb.table("tickets")
        .insert({
            "name": name,
            "email": email,
            "module": module,
            "subject": subject,
            "description": description,
            "priority": priority,
            "session_id": session_id,
            "status": "open",
        })
        .execute()
    )
    ticket_id = str(result.data[0]["id"])
    logger.info("Ticket created: %s | %s | %s | %s", ticket_id, priority, module, subject)

    # TODO: forward to external project management system when ready
    # _forward_to_external(ticket_id, ...)

    return ticket_id
