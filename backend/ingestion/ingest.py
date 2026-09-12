"""
PDF ingestion pipeline — OCR edition with checkpoint support.

Because AdminIE PDFs are scanned images (no selectable text), each page is
rendered to a PNG with PyMuPDF and transcribed by GPT-4o-mini Vision.
OCR results are saved to a checkpoint file so they never need to be re-run.
The embed+upsert step can be retried independently via --embed-only.

Usage:
    python -m backend.ingestion.ingest               # full run (OCR + embed)
    python -m backend.ingestion.ingest --embed-only  # skip OCR, use checkpoint
    python -m backend.ingestion.ingest --clear       # wipe Supabase first
"""

import os
import re
import json
import time
from pathlib import Path

import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded, ServiceUnavailable
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from langchain_core.documents import Document
from backend.app.gemini_embeddings import GeminiEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client

load_dotenv()

DATA_DIR = Path(__file__).parents[1] / "data"
CHECKPOINT_FILE = Path(__file__).parent / "ocr_checkpoint.json"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
DPI = 150
OCR_MODEL = "gemini-2.0-flash"


def _module_name(path: Path) -> str:
    return re.sub(r"[_-]", " ", path.parent.name).title()


def _page_to_bytes(page: fitz.Page, dpi: int = DPI) -> bytes:
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return pix.tobytes("png")


@retry(
    retry=retry_if_exception_type((ResourceExhausted, DeadlineExceeded, ServiceUnavailable)),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)
def _ocr_page(image_bytes: bytes) -> str:
    model = genai.GenerativeModel(OCR_MODEL)
    response = model.generate_content([
        "Extract all text from this document page exactly as it appears. "
        "Preserve headings, bullet points, tables, and numbered lists. "
        "Do not summarise — output the raw text only.",
        {"mime_type": "image/png", "data": image_bytes},
    ])
    return response.text or ""


def _save_checkpoint(docs: list[Document]) -> None:
    data = [
        {"page_content": d.page_content, "metadata": d.metadata}
        for d in docs
    ]
    CHECKPOINT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Checkpoint saved: {CHECKPOINT_FILE}")


def _load_checkpoint() -> list[Document]:
    data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in data]
    print(f"Loaded {len(docs)} pages from checkpoint.")
    return docs


def run_ocr() -> list[Document]:
    genai.configure(api_key=os.environ["GOOGLE_AI_API_KEY"])
    docs: list[Document] = []
    pdf_files = sorted(DATA_DIR.rglob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found under {DATA_DIR}")

    for pdf_path in pdf_files:
        module = _module_name(pdf_path)
        source = str(pdf_path.relative_to(DATA_DIR))
        print(f"  OCR-ing: {source}")

        pdf_doc = fitz.open(str(pdf_path))
        page_count = len(pdf_doc)
        for page_num in range(page_count):
            image_bytes = _page_to_bytes(pdf_doc[page_num])
            text = _ocr_page(image_bytes)
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": source, "module": module, "page": page_num + 1},
                ))
            time.sleep(1.5)

        pdf_doc.close()
        print(f"    -> {page_count} pages processed")

    print(f"OCR complete: {len(docs)} pages from {len(pdf_files)} PDFs.")
    _save_checkpoint(docs)
    return docs


def split_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks.")
    return chunks


def embed_and_upsert(chunks: list[Document], supabase, embeddings) -> None:
    print(f"Embedding and upserting {len(chunks)} chunks to Supabase...")
    SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=supabase,
        table_name="documents",
        query_name="match_documents",
        chunk_size=500,
    )
    print(f"Done. {len(chunks)} chunks stored in Supabase.")


def ingest(clear_existing: bool = False, embed_only: bool = False) -> None:
    print("=== AdminIEBot Ingestion Pipeline ===")

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    embeddings = GeminiEmbeddings(
        model="gemini-embedding-001",
        api_key=os.environ["GOOGLE_AI_API_KEY"],
    )

    if clear_existing:
        print("Clearing existing PDF documents (Google Doc chunks preserved)...")
        supabase.table("documents").delete().neq("metadata->>source", "google_doc").execute()

    if embed_only:
        if not CHECKPOINT_FILE.exists():
            raise FileNotFoundError(
                "No checkpoint found. Run without --embed-only first to generate OCR data."
            )
        docs = _load_checkpoint()
    else:
        docs = run_ocr()

    chunks = split_documents(docs)
    embed_and_upsert(chunks, supabase, embeddings)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Wipe Supabase documents before upserting")
    parser.add_argument("--embed-only", action="store_true", help="Skip OCR, use saved checkpoint")
    args = parser.parse_args()
    ingest(clear_existing=args.clear, embed_only=args.embed_only)
