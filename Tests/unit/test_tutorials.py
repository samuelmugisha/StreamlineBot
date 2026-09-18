"""Unit tests for backend.app.tutorials path/URL helpers."""

import os

from backend.app.tutorials import tutorial_image_url, tutorial_storage_path


def test_storage_path_replaces_extension_with_page_png():
    assert tutorial_storage_path("Crm/CRM_module.pdf", 8) == "Crm/CRM_module/page-8.png"


def test_storage_path_normalises_windows_separators():
    assert tutorial_storage_path("Crm\\CRM_module.pdf", 8) == "Crm/CRM_module/page-8.png"


def test_storage_path_handles_nested_folders():
    assert (
        tutorial_storage_path("banking/subfolder/banking_module.pdf", 1)
        == "banking/subfolder/banking_module/page-1.png"
    )


def test_tutorial_image_url_builds_public_storage_url():
    url = tutorial_image_url("Finance/finance_module.pdf", 5)
    supabase_url = os.environ["SUPABASE_URL"]
    assert url == f"{supabase_url}/storage/v1/object/public/tutorials/Finance/finance_module/page-5.png"
