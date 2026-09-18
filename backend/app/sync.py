"""
Background sync loop — polls Google Drive every GDOC_SYNC_INTERVAL_MINUTES
and re-ingests the knowledge base doc when it detects a change.
"""

import asyncio
import logging
import os

from supabase import create_client

logger = logging.getLogger(__name__)

_GDOC_STATE_KEY = "gdoc_last_modified"


def _supabase():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def _load_state() -> dict:
    resp = _supabase().table("sync_state").select("value").eq("key", _GDOC_STATE_KEY).execute()
    if resp.data:
        return {"last_modified": resp.data[0]["value"]}
    return {"last_modified": None}


def _save_state(state: dict) -> None:
    _supabase().table("sync_state").upsert(
        {"key": _GDOC_STATE_KEY, "value": state.get("last_modified")},
    ).execute()


def _check_and_sync() -> None:
    # Google Doc sync (AdminIE)
    doc_id = os.environ.get("GOOGLE_DOC_ID")
    if doc_id:
        from backend.ingestion.gdoc_ingest import get_modified_time, ingest_gdoc

        state = _load_state()
        current_modified = get_modified_time(doc_id)

        if current_modified == state.get("last_modified"):
            logger.info("Google Doc unchanged (%s) — no sync needed.", current_modified)
        else:
            logger.info(
                "Google Doc changed: %s → %s. Re-ingesting...",
                state.get("last_modified", "never"),
                current_modified,
            )
            chunks = ingest_gdoc()
            _save_state({"last_modified": current_modified})
            logger.info("Sync complete — %d chunks stored.", chunks)

    # Google Drive PDF sync (Streamline)
    gdrive_folder = os.environ.get("GDRIVE_FOLDER_ID")
    if gdrive_folder:
        from backend.ingestion.gdrive_ingest import sync_gdrive

        sync_gdrive()

    if not doc_id and not gdrive_folder:
        logger.warning("Neither GOOGLE_DOC_ID nor GDRIVE_FOLDER_ID set — skipping sync.")


async def start_sync_loop() -> asyncio.Task:
    interval = int(os.environ.get("GDOC_SYNC_INTERVAL_MINUTES", 30)) * 60

    async def _loop():
        while True:
            await asyncio.sleep(interval)
            try:
                await asyncio.to_thread(_check_and_sync)
            except Exception:
                logger.exception("Google Doc sync failed — will retry next interval.")

    task = asyncio.create_task(_loop())
    logger.info(
        "Google Doc sync loop started (interval: %d min).",
        interval // 60,
    )
    return task
