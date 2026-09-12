"""Shared helpers for the "tutorial visual" feature.

Maps a PDF source path + page number to its location in the Supabase
Storage "tutorials" bucket. Used by both /chat (to build the image URL
returned to the widget) and backend/ingestion/export_tutorial_images.py
(to upload the rendered pages).
"""

import os

TUTORIAL_BUCKET = "tutorials"


def tutorial_storage_path(source: str, page: int) -> str:
    """e.g. 'Crm/CRM_module.pdf', 8 -> 'Crm/CRM_module/page-8.png'

    `source` comes from documents.metadata, which stores OS-native path
    separators from ingestion (backslashes on Windows) — normalise to "/"
    to match the Storage object paths uploaded by export_tutorial_images.py.
    """
    stem = source.replace("\\", "/").rsplit(".", 1)[0]
    return f"{stem}/page-{page}.png"


def tutorial_image_url(source: str, page: int) -> str:
    path = tutorial_storage_path(source, page)
    return f"{os.environ['SUPABASE_URL']}/storage/v1/object/public/{TUTORIAL_BUCKET}/{path}"
