"""
Google Docs ingestion — fetches the AdminIE knowledge base doc,
clears old chunks, and re-embeds into Supabase.

The doc is organised as one tab per module, with each Q&A entry followed by
an inline screenshot of the actual feature being described. Ingestion walks
each tab's content, groups every question + answer with the screenshot that
follows it, uploads that screenshot to Supabase Storage, and stores its URL
directly on the chunk's metadata — so /chat can link to the real tutorial
image for that exact question instead of a generic PDF page render.

Called automatically by the sync loop in backend/app/sync.py whenever
the doc's modifiedTime changes.
"""

import os
import re
import io
import json
import socket
import hashlib
import logging

import requests
from PIL import Image
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from langchain_core.documents import Document
from backend.app.gemini_embeddings import GeminiEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

load_dotenv()

logger = logging.getLogger(__name__)

# The Google API client (httplib2-based) has no timeout by default, so a
# stalled connection can hang the whole ingestion run indefinitely — unlike
# requests/supabase calls below, which all set explicit timeouts. This bounds
# every socket op in the process as a safety net.
socket.setdefaulttimeout(60)

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

CHUNK_SIZE         = 1000
CHUNK_OVERLAP      = 150
SOURCE_TAG         = "google_doc"
SCREENSHOT_BUCKET  = "gdoc-screenshots"

# "Questions" is a bare table-of-contents tab — every question already
# answered in its own module tab, repeated here with no answer text and no
# images. Each line is then a near-exact embedding match for its own
# question, so it kept winning the top retrieval slot ahead of the real
# answer and starving it of its tutorial image. Pure noise — exclude it.
EXCLUDED_TABS = {"Questions"}

# Supabase key for the image manifest (path → md5 hash). Stored in the
# sync_state table so it survives container restarts and we don't re-upload
# every screenshot on each redeploy.
_MANIFEST_KEY = "gdoc_image_manifest"


def _load_image_manifest(supabase) -> dict:
    resp = supabase.table("sync_state").select("value").eq("key", _MANIFEST_KEY).execute()
    if resp.data and resp.data[0].get("value"):
        return json.loads(resp.data[0]["value"])
    return {}


def _save_image_manifest(supabase, manifest: dict) -> None:
    supabase.table("sync_state").upsert(
        {"key": _MANIFEST_KEY, "value": json.dumps(manifest)},
    ).execute()


def _build_services():
    # GOOGLE_CREDENTIALS_JSON (the service account key's raw JSON, set as a
    # platform secret) is what production uses — the key file itself is
    # gitignored and never makes it into a container build. GOOGLE_CREDENTIALS_FILE
    # is kept as a fallback for local dev, where the file is on disk.
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds_path = Path(os.environ["GOOGLE_CREDENTIALS_FILE"])
        creds = service_account.Credentials.from_service_account_file(
            str(creds_path), scopes=SCOPES
        )
    docs_svc  = build("docs",  "v1", credentials=creds, cache_discovery=False)
    drive_svc = build("drive", "v3", credentials=creds, cache_discovery=False)
    return docs_svc, drive_svc


def get_modified_time(doc_id: str) -> str:
    """Return the RFC3339 modifiedTime string for the doc."""
    _, drive_svc = _build_services()
    meta = drive_svc.files().get(fileId=doc_id, fields="modifiedTime").execute()
    return meta["modifiedTime"]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "tab"


def _ensure_screenshot_bucket(supabase) -> None:
    try:
        supabase.storage.create_bucket(SCREENSHOT_BUCKET, options={"public": True})
        logger.info("Created public bucket '%s'.", SCREENSHOT_BUCKET)
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise


@retry(
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _download_image(content_uri: str) -> requests.Response:
    resp = requests.get(content_uri, timeout=30)
    resp.raise_for_status()
    return resp


def _download_inline_image_bytes(inline_object: dict) -> tuple[bytes, str] | None:
    """Download one tab's inline image from its short-lived Google-hosted URI.
    Returns (bytes, content_type), or None if there's nothing to download."""
    if not inline_object:
        return None
    image_props = (
        inline_object.get("inlineObjectProperties", {})
        .get("embeddedObject", {})
        .get("imageProperties", {})
    )
    content_uri = image_props.get("contentUri")
    if not content_uri:
        return None
    resp = _download_image(content_uri)
    return resp.content, resp.headers.get("Content-Type", "image/png")


def _stitch_images(image_data: list[tuple[bytes, str]]) -> tuple[bytes, str]:
    """Combine a question's screenshots (one per step) into a single tall
    image, so multi-step answers still get exactly one tutorial link."""
    if len(image_data) == 1:
        return image_data[0]

    gap = 14
    images = [Image.open(io.BytesIO(raw)).convert("RGB") for raw, _ in image_data]
    width = max(im.width for im in images)
    resized = []
    for im in images:
        if im.width != width:
            im = im.resize((width, round(im.height * width / im.width)))
        resized.append(im)

    canvas = Image.new("RGB", (width, sum(im.height for im in resized) + gap * (len(resized) - 1)), (225, 225, 225))
    y = 0
    for im in resized:
        canvas.paste(im, (0, y))
        y += im.height + gap

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), "image/png"


def _finalize_qa_image(
    supabase, manifest: dict, tab_slug: str, q_idx: int, image_data: list[tuple[bytes, str]]
) -> str | None:
    """Stitch (if needed) and upload the screenshot(s) collected for one Q&A.
    Skips the upload if the result is byte-for-byte identical to what's
    already there, per the manifest's recorded hash."""
    if not image_data:
        return None

    content, content_type = _stitch_images(image_data)
    ext = "jpg" if "jpeg" in content_type else "png"
    path = f"{tab_slug}/q-{q_idx:03d}.{ext}"
    url = f"{os.environ['SUPABASE_URL']}/storage/v1/object/public/{SCREENSHOT_BUCKET}/{path}"

    digest = hashlib.md5(content).hexdigest()
    if manifest.get(path) == digest:
        return url

    supabase.storage.from_(SCREENSHOT_BUCKET).upload(
        path, content,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    manifest[path] = digest
    return url


def _parse_tab(tab: dict, doc_id: str, supabase, manifest: dict) -> list[Document]:
    """Walk one tab's paragraphs, grouping text into one chunk per question.
    A new question is detected by the paragraph ending in "?" (true for both
    the numbered and unnumbered tabs) rather than by hitting an image — a
    single question can have several steps, each with its own screenshot, and
    those all belong to the same answer rather than splitting it apart."""
    title = tab.get("tabProperties", {}).get("title", "untitled")
    slug = _slugify(title)
    doc_tab = tab.get("documentTab", {})
    inline_objects = doc_tab.get("inlineObjects", {})
    content = doc_tab.get("body", {}).get("content", [])

    docs: list[Document] = []
    buffer: list[str] = []
    pending_images: list[tuple[bytes, str]] = []
    q_idx = 0
    image_count = 0

    def flush() -> None:
        nonlocal buffer, pending_images, q_idx
        text = "\n".join(buffer).strip()
        buffer = []
        images, pending_images = pending_images, []
        if not text:
            return
        try:
            image_url = _finalize_qa_image(supabase, manifest, slug, q_idx, images)
        except Exception:
            logger.exception(
                "Failed to finalize image(s) for tab %r question %d — keeping the text, dropping the image.",
                title, q_idx,
            )
            image_url = None
        q_idx += 1
        metadata = {"source": SOURCE_TAG, "doc_id": doc_id, "module": title}
        if image_url:
            metadata["image_url"] = image_url
        docs.append(Document(page_content=text, metadata=metadata))

    for block in content:
        para = block.get("paragraph")
        if not para:
            continue
        elements = para.get("elements", [])
        image_id = next(
            (el["inlineObjectElement"]["inlineObjectId"]
             for el in elements if "inlineObjectElement" in el),
            None,
        )
        if image_id:
            try:
                data = _download_inline_image_bytes(inline_objects.get(image_id))
            except Exception:
                logger.exception("Failed to download an image for tab %r — skipping it.", title)
                data = None
            if data:
                pending_images.append(data)
            image_count += 1
            if image_count % 20 == 0:
                logger.info("  %s: %d/%d images downloaded", title, image_count, len(inline_objects))
            continue

        text = "".join(el.get("textRun", {}).get("content", "") for el in elements)
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.endswith("?") and buffer:
            flush()
        buffer.append(text.rstrip("\n"))

    flush()  # trailing Q&A with no question mark after it

    for child in tab.get("childTabs", []):
        docs.extend(_parse_tab(child, doc_id, supabase, manifest))

    return docs


def fetch_gdoc_tab_documents(doc_id: str, supabase, manifest: dict) -> list[Document]:
    """Fetch the doc and return one Document per Q&A block (or per
    paragraph-run, for tabs without images), across all tabs."""
    docs_svc, _ = _build_services()
    doc = docs_svc.documents().get(documentId=doc_id, includeTabsContent=True).execute()

    tabs = doc.get("tabs")
    if tabs:
        all_docs = []
        for tab in tabs:
            title = tab.get("tabProperties", {}).get("title", "untitled")
            if title in EXCLUDED_TABS:
                logger.info("Skipping tab %r (excluded).", title)
                continue
            logger.info("Processing tab %r ...", title)
            all_docs.extend(_parse_tab(tab, doc_id, supabase, manifest))
        return all_docs

    # Fallback for docs with no tabs at all.
    lines = []
    for block in doc.get("body", {}).get("content", []):
        para = block.get("paragraph")
        if not para:
            continue
        text = "".join(el.get("textRun", {}).get("content", "") for el in para.get("elements", []))
        if text.strip():
            lines.append(text.rstrip("\n"))
    text = "\n".join(lines)
    if not text.strip():
        return []
    return [Document(page_content=text, metadata={"source": SOURCE_TAG, "doc_id": doc_id})]


def ingest_gdoc() -> int:
    """
    Clear existing Google Doc chunks from Supabase and re-ingest from
    the current doc content. Returns the number of chunks stored.
    """
    doc_id = os.environ["GOOGLE_DOC_ID"]

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    _ensure_screenshot_bucket(supabase)

    manifest = _load_image_manifest(supabase)
    logger.info("Fetching Google Doc %s ...", doc_id)
    try:
        tab_docs = fetch_gdoc_tab_documents(doc_id, supabase, manifest)
    finally:
        # Persist whatever progress was made even if a later tab fails, so a
        # retry doesn't re-upload images that already succeeded this run.
        _save_image_manifest(supabase, manifest)
    if not tab_docs:
        raise ValueError("Google Doc returned empty content — check sharing permissions.")

    embeddings = GeminiEmbeddings(
        model="gemini-embedding-001",
        api_key=os.environ["GOOGLE_AI_API_KEY"],
    )

    # Q&A blocks are already small and bounded by their own image, so the
    # splitter leaves them as single chunks — it only breaks up the longer,
    # image-less blobs (e.g. table-of-contents tabs).
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(tab_docs)
    logger.info("Split into %d chunks. Embedding and upserting...", len(chunks))

    # Snapshot IDs of the existing chunks BEFORE embedding new ones.
    # We delete by ID after a successful embed so that if OpenAI fails,
    # the old chunks survive intact instead of leaving the KB empty.
    old_resp = supabase.table("documents").select("id").filter(
        "metadata->>source", "eq", SOURCE_TAG
    ).execute()
    old_ids = [row["id"] for row in (old_resp.data or [])]

    SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=supabase,
        table_name="documents",
        query_name="match_documents",
        chunk_size=500,
    )

    # Delete only the old IDs — new ones (inserted above) are untouched.
    if old_ids:
        logger.info("Removing %d old Google Doc chunks...", len(old_ids))
        batch = 100
        for i in range(0, len(old_ids), batch):
            supabase.table("documents").delete().in_("id", old_ids[i:i + batch]).execute()

    logger.info("Google Doc sync complete — %d chunks stored.", len(chunks))
    return len(chunks)
