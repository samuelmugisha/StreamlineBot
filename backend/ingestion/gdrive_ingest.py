"""
Google Drive PDF ingestion + live sync for Streamline Health Tech.

First run: OCRs all PDFs in the shared folder, uploads page screenshots to
Supabase Storage, and stores text embeddings in Supabase.

Subsequent sync calls (from the background loop in backend/app/sync.py):
- Lists all PDFs and their modifiedTime from Google Drive
- Re-ingests only files that changed or were added
- Removes embeddings for files that were deleted from Drive

No local disk storage needed — PDFs are downloaded into memory one at a time.
Loads credentials from .env.streamline (never touches AdminIE's .env).

Usage (one-time / manual re-run):
    python -m backend.ingestion.gdrive_ingest              # full OCR + embed
    python -m backend.ingestion.gdrive_ingest --embed-only # skip OCR, use checkpoint
"""

import base64
import io
import json
import logging
import os
import re
import time
from pathlib import Path

import fitz
import requests
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from supabase import create_client

from backend.app.gemini_embeddings import GeminiEmbeddings

load_dotenv(Path(__file__).parents[2] / ".env.streamline")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GDRIVE_FOLDER_ID = "16FmmLzhDoUqWpHngTmNT217VmcClwqos"
CHECKPOINT_FILE = Path(__file__).parent / "gdrive_checkpoint.json"
STATE_FILE = Path(__file__).parent / "gdrive_sync_state.json"
TUTORIAL_BUCKET = "tutorials"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
DPI = 150
OCR_MODEL = "gemini-2.0-flash"

_BAD_OCR_PHRASES = (
    "i'm sorry, but i can't assist",
    "i'm sorry, but i cannot assist",
    "i'm unable to extract",
    "i cannot assist with",
    "sorry, i can't help",
    "i'm not able to assist",
    "i can't extract text from images",
    "i cannot extract text from images",
    "if you provide the text content",
)

_CODE_FENCE = re.compile(r"^```[a-z]*\n?", re.MULTILINE)


def _clean_ocr(text: str) -> str:
    """Strip markdown code fences that gpt-4o-mini sometimes wraps output in."""
    text = _CODE_FENCE.sub("", text)
    text = text.replace("```", "")
    return text.strip()


def _is_garbage(text: str) -> bool:
    """Return True for blank/near-blank pages and known bad OCR refusals."""
    t = text.lower().strip()
    if len(t) < 100:
        return True
    return any(phrase in t for phrase in _BAD_OCR_PHRASES)


def _is_toc_page(text: str) -> bool:
    """Return True for Table of Contents pages — detected by the header text."""
    return bool(re.search(r"table\s+of\s+contents", text, re.IGNORECASE))


# ── Google Drive helpers ───────────────────────────────────────────────────────


def _build_drive():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    if creds_json:
        creds = service_account.Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    elif creds_file:
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    else:
        raise ValueError("Set GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDENTIALS_FILE in .env.streamline")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_pdfs(drive, folder_id: str) -> list[dict]:
    """Return [{file_id, file_name, folder_name, modified_time}] for all PDFs
    visible to the service account. Uses folder_id only to name the root level;
    derives module name from each PDF's parent folder name."""

    # Build a map of folder_id → folder_name scoped to the configured folder's
    # direct children only — prevents ingesting PDFs from unrelated Drive folders
    # the service account can see.
    folder_map: dict[str, str] = {folder_id: "General"}
    folders_resp = (
        drive.files()
        .list(
            q=f"mimeType='application/vnd.google-apps.folder' and trashed=false and '{folder_id}' in parents",
            fields="files(id,name)",
            pageSize=200,
        )
        .execute()
    )
    for f in folders_resp.get("files", []):
        folder_map[f["id"]] = f["name"]

    # List PDFs and keep only those whose parent is in the scoped folder map.
    results = []
    page_token = None
    while True:
        kwargs = dict(
            q="mimeType='application/pdf' and trashed=false",
            fields="nextPageToken,files(id,name,parents,modifiedTime)",
            pageSize=200,
        )
        if page_token:
            kwargs["pageToken"] = page_token
        resp = drive.files().list(**kwargs).execute()
        for f in resp.get("files", []):
            parent_id = (f.get("parents") or [None])[0]
            if parent_id not in folder_map:
                continue  # PDF is outside the configured folder — skip
            folder_name = folder_map[parent_id]
            results.append(
                {
                    "file_id": f["id"],
                    "file_name": f["name"],
                    "folder_name": folder_name,
                    "modified_time": f["modifiedTime"],
                }
            )
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return results


def _download_pdf(drive, file_id: str) -> bytes:
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, drive.files().get_media(fileId=file_id))
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


# ── OCR ───────────────────────────────────────────────────────────────────────


def _ocr_page(image_bytes: bytes) -> str:
    model = os.environ.get("STREAMLINE_OCR_MODEL", OCR_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Extract all text from this document page exactly as it appears. Preserve headings, bullet points, tables, and numbered lists. Do not summarise — output the raw text only."
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(image_bytes).decode(),
                        }
                    },
                ]
            }
        ]
    }
    headers = {"x-goog-api-key": os.environ["GOOGLE_AI_API_KEY"], "Content-Type": "application/json"}
    for attempt in range(12):
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code in (429, 500, 503):
            sleep_s = min(10 * (2**attempt), 120)
            logger.warning(
                "OCR HTTP %d — sleeping %ds (attempt %d/12)", resp.status_code, sleep_s, attempt + 1
            )
            time.sleep(sleep_s)
            continue
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    raise RuntimeError("OCR failed after 12 attempts")


# ── Per-file ingestion ─────────────────────────────────────────────────────────


def _ingest_pdf(entry: dict, drive, supabase, bucket) -> list[Document]:
    """Download, OCR, screenshot-upload one PDF. Returns its Document pages."""
    folder = entry["folder_name"]
    fname = entry["file_name"]
    source = f"{folder}/{fname}"
    logger.info("  Ingesting: %s", source)

    pdf_bytes = _download_pdf(drive, entry["file_id"])
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    docs: list[Document] = []

    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        png_bytes = pix.tobytes("png")

        # Use the single embedded image if there is exactly one and it is large
        # enough to be a real UI screenshot (not a small logo or icon).
        embedded = page.get_images(full=True)
        screenshot_bytes = png_bytes
        if len(embedded) == 1:
            try:
                img_data = pdf_doc.extract_image(embedded[0][0])
                if img_data["width"] > 150 and img_data["height"] > 150:
                    screenshot_bytes = img_data["image"]
            except Exception:
                pass

        # Upload screenshot
        stem = source.rsplit(".", 1)[0]
        storage_path = f"{stem}/page-{page_num + 1}.png"
        try:
            bucket.upload(
                storage_path, screenshot_bytes, file_options={"content-type": "image/png", "upsert": "true"}
            )
        except Exception as e:
            logger.warning("    Screenshot upload failed %s: %s", storage_path, e)

        text = _clean_ocr(_ocr_page(png_bytes))
        if text.strip() and not _is_garbage(text) and not _is_toc_page(text):
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": source, "module": folder, "page": page_num + 1},
                )
            )
        elif text.strip():
            logger.debug("    Skipped page %d (blank/bad OCR/TOC)", page_num + 1)
        time.sleep(5)

    page_count = len(pdf_doc)
    pdf_doc.close()
    logger.info("    -> %d pages", page_count)
    return docs


def _delete_pdf_chunks(supabase, source: str) -> None:
    """Remove all embedded chunks for a specific PDF source path."""
    supabase.table("documents").delete().filter("metadata->>source", "eq", source).execute()


def _source_to_query(source: str) -> str:
    """Turn 'Inventory/Drugs Management.pdf' into a retrieval test query."""
    return Path(source).stem.replace("-", " ").replace("_", " ")


def _test_retrieval(supabase, embeddings, source: str) -> None:
    """After embedding a PDF, run a quick retrieval check to verify it worked."""
    count_resp = (
        supabase.table("documents")
        .select("id", count="exact")
        .filter("metadata->>source", "eq", source)
        .execute()
    )
    chunk_count = count_resp.count or 0
    if chunk_count == 0:
        logger.error("  [TEST] FAIL — 0 chunks found in DB for %s", source)
        return

    query_text = _source_to_query(source)
    embedding = embeddings.embed_query(query_text)
    rows = (
        supabase.rpc(
            "match_documents",
            {
                "query_embedding": embedding,
                "match_count": 5,
                "match_threshold": 0.0,
            },
        ).execute()
    ).data or []

    logger.info("  [TEST] %d chunks embedded | query: '%s'", chunk_count, query_text)
    for row in rows[:3]:
        logger.info(
            "    sim=%.3f | %s | page %s",
            row["similarity"],
            row["metadata"].get("source", "?"),
            row["metadata"].get("page", "?"),
        )

    if rows and rows[0]["metadata"].get("source") == source:
        logger.info("  [TEST] PASS — top result is from this PDF (sim=%.3f)", rows[0]["similarity"])
    elif rows:
        same = [r for r in rows if r["metadata"].get("source") == source]
        if same:
            logger.warning("  [TEST] WARN — this PDF not #1; found at position %d", rows.index(same[0]) + 1)
        else:
            logger.warning(
                "  [TEST] WARN — this PDF not in top 5 results; top is %s", rows[0]["metadata"].get("source")
            )
    else:
        logger.warning("  [TEST] WARN — no results at threshold=0.0 (very unusual)")


def _embed_and_upsert(docs: list[Document], supabase, embeddings) -> None:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    if not chunks:
        return
    SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=supabase,
        table_name="documents",
        query_name="match_documents",
        chunk_size=50,
    )
    logger.info("  Upserted %d chunks", len(chunks))


# ── State file ─────────────────────────────────────────────────────────────────


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"files": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Public API ─────────────────────────────────────────────────────────────────


def sync_gdrive() -> None:
    """
    Called by the background sync loop. Compares Drive file modifiedTimes against
    the local state file and re-ingests only what changed.
    """
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", GDRIVE_FOLDER_ID)
    if not folder_id:
        logger.warning("GDRIVE_FOLDER_ID not set — skipping Drive sync.")
        return

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    embeddings = GeminiEmbeddings(model="gemini-embedding-001", api_key=os.environ["GOOGLE_AI_API_KEY"])
    drive = _build_drive()
    bucket = supabase.storage.from_(TUTORIAL_BUCKET)

    current_files = {e["file_id"]: e for e in _list_pdfs(drive, folder_id)}
    state = _load_state()
    previous_files = state.get("files", {})

    # State file is wiped on every container restart — rebuild from Supabase
    # so we don't re-ingest PDFs that are already embedded.
    if not previous_files:
        logger.info("No local sync state found — checking Supabase for existing chunks...")
        for fid, entry in current_files.items():
            source = f"{entry['folder_name']}/{entry['file_name']}"
            count_resp = (
                supabase.table("documents")
                .select("id", count="exact")
                .filter("metadata->>source", "eq", source)
                .execute()
            )
            if (count_resp.count or 0) > 0:
                previous_files[fid] = {
                    "file_name": entry["file_name"],
                    "folder_name": entry["folder_name"],
                    "modified_time": entry["modified_time"],
                }
                logger.info("  %s — already in Supabase, skipping", source)
        if previous_files:
            logger.info("Rebuilt sync state from Supabase for %d PDFs.", len(previous_files))

    changed = [
        entry
        for fid, entry in current_files.items()
        if previous_files.get(fid, {}).get("modified_time") != entry["modified_time"]
    ]
    removed = [prev for fid, prev in previous_files.items() if fid not in current_files]

    if not changed and not removed:
        logger.info("Google Drive unchanged — no sync needed.")
        return

    logger.info("%d changed/new, %d removed PDFs — syncing...", len(changed), len(removed))

    for prev in removed:
        source = f"{prev['folder_name']}/{prev['file_name']}"
        logger.info("  Removing: %s", source)
        _delete_pdf_chunks(supabase, source)

    for entry in changed:
        source = f"{entry['folder_name']}/{entry['file_name']}"
        _delete_pdf_chunks(supabase, source)
        docs = _ingest_pdf(entry, drive, supabase, bucket)
        _embed_and_upsert(docs, supabase, embeddings)

    # Update state
    state["files"] = {
        fid: {
            "file_name": e["file_name"],
            "folder_name": e["folder_name"],
            "modified_time": e["modified_time"],
        }
        for fid, e in current_files.items()
    }
    _save_state(state)
    logger.info("Google Drive sync complete.")


def run(embed_only: bool = False) -> None:
    """Full first-time ingestion run."""
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    embeddings = GeminiEmbeddings(model="gemini-embedding-001", api_key=os.environ["GOOGLE_AI_API_KEY"])

    # Ensure tutorials bucket is public
    try:
        supabase.storage.create_bucket(TUTORIAL_BUCKET, options={"public": True})
        logger.info("Created public bucket '%s'", TUTORIAL_BUCKET)
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise

    bucket = supabase.storage.from_(TUTORIAL_BUCKET)

    if embed_only:
        if not CHECKPOINT_FILE.exists():
            raise FileNotFoundError("No checkpoint found. Run without --embed-only first.")
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        all_docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in data]
        logger.info("Loaded %d pages from checkpoint.", len(all_docs))
        _embed_and_upsert(all_docs, supabase, embeddings)
    else:
        drive = _build_drive()
        pdf_list = _list_pdfs(drive, GDRIVE_FOLDER_ID)
        logger.info("Found %d PDFs across all folders", len(pdf_list))

        all_docs: list[Document] = []
        for i, entry in enumerate(pdf_list, 1):
            source = f"{entry['folder_name']}/{entry['file_name']}"
            logger.info("[%d/%d] %s", i, len(pdf_list), source)
            try:
                # Skip PDFs already embedded (enables safe resume after failure)
                count_resp = (
                    supabase.table("documents")
                    .select("id", count="exact")
                    .filter("metadata->>source", "eq", source)
                    .execute()
                )
                if (count_resp.count or 0) > 0:
                    logger.info("  Already embedded (%d chunks) — skipping", count_resp.count)
                    continue
                docs = _ingest_pdf(entry, drive, supabase, bucket)
                if docs:
                    _embed_and_upsert(docs, supabase, embeddings)
                    _test_retrieval(supabase, embeddings, source)
                    all_docs.extend(docs)
                else:
                    logger.warning("  Skipped — 0 content pages extracted from %s", source)
            except Exception as e:
                logger.warning("  FAILED to ingest %s: %s", source, e)

        CHECKPOINT_FILE.write_text(
            json.dumps(
                [{"page_content": d.page_content, "metadata": d.metadata} for d in all_docs],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("Checkpoint saved: %d pages total", len(all_docs))

        state = {
            "files": {
                e["file_id"]: {
                    "file_name": e["file_name"],
                    "folder_name": e["folder_name"],
                    "modified_time": e["modified_time"],
                }
                for e in pdf_list
            }
        }
        _save_state(state)

    logger.info("Done.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--embed-only", action="store_true", help="Skip OCR, use saved checkpoint")
    args = parser.parse_args()
    run(embed_only=args.embed_only)
