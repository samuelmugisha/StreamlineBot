"""
One-time export of PDF pages as PNG images, for the "tutorial visual" feature.

Renders every page of every PDF in backend/data/ to a PNG (same rendering
used by the OCR pipeline) and uploads it to the Supabase Storage "tutorials"
bucket, at the path backend.app.tutorials.tutorial_storage_path expects.
/chat links to these images for whichever page best matches the user's
question.

Re-running this script is safe — uploads overwrite existing files.

Usage:
    python -m backend.ingestion.export_tutorial_images
"""

import os
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv
from supabase import create_client

from backend.app.tutorials import TUTORIAL_BUCKET, tutorial_storage_path

load_dotenv()

DATA_DIR = Path(__file__).parents[1] / "data"
DPI = 150


def export_images() -> None:
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    try:
        supabase.storage.create_bucket(TUTORIAL_BUCKET, options={"public": True})
        print(f"Created public bucket '{TUTORIAL_BUCKET}'.")
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise

    bucket = supabase.storage.from_(TUTORIAL_BUCKET)
    pdf_files = sorted(DATA_DIR.rglob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found under {DATA_DIR}")

    zoom = DPI / 72
    mat = fitz.Matrix(zoom, zoom)

    for pdf_path in pdf_files:
        source = str(pdf_path.relative_to(DATA_DIR)).replace("\\", "/")
        print(f"Exporting: {source}")

        pdf_doc = fitz.open(str(pdf_path))
        page_count = len(pdf_doc)
        for page_num in range(page_count):
            pix = pdf_doc[page_num].get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            png_bytes = pix.tobytes("png")
            path = tutorial_storage_path(source, page_num + 1)
            bucket.upload(
                path, png_bytes,
                file_options={"content-type": "image/png", "upsert": "true"},
            )
        pdf_doc.close()
        print(f"  -> {page_count} pages uploaded")

    print("Done.")


if __name__ == "__main__":
    export_images()
