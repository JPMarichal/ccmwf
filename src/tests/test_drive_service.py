"""Tests for `DriveService` helpers and unique filename logic."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from app.config import Settings
from app.services.drive_service import DriveService


@pytest.fixture
def drive_settings(tmp_path):
    credentials_path = tmp_path / "creds.json"
    credentials_path.write_text("{}")
    return Settings(
        gmail_user="user@test.com",
        gmail_app_password="pass",
        processed_label="processed",
        google_drive_credentials_path=str(credentials_path),
        google_drive_attachments_folder_id="folder-root",
    )


@pytest.fixture
def drive_service(drive_settings):
    service = DriveService(drive_settings)
    service._service = MagicMock()
    service._ensure_service = MagicMock()
    return service


def _files_service(existing_names):
    def list_fn(**kwargs):
        return SimpleNamespace(execute=lambda: {"files": [{"name": name} for name in existing_names]})

    files_mock = MagicMock()
    files_mock.list.side_effect = list_fn
    return files_mock


def test_format_filename_sanitizes_components(drive_service):
    result = drive_service.format_filename("20250110", "Distrito Norte", "Reporte Final (v1).pdf")
    assert result.startswith("20250110_Distrito_Norte_Reporte_Final_(v1).pdf")
    assert " " not in result
    assert "__" not in result


def test_format_filename_strips_gender_prefix_when_followed_by_digits(drive_service):
    result = drive_service.format_filename("20250110", "14A", "F_14A_doc.pdf")
    assert result.startswith("20250110_14A_doc.pdf")


def test_format_filename_avoids_duplicate_district_component(drive_service):
    result = drive_service.format_filename("20250922", "Distrito_10C", "F_Distrito_10C.pdf")
    assert result == "20250922_Distrito_10C.pdf"


def test_format_filename_removes_prefixes_from_district_values(drive_service):
    result = drive_service.format_filename("20250922", "F District 10C", "District 10C.pdf")
    assert result == "20250922_District_10C.pdf"


def test_guess_primary_district_strips_single_letter_prefixes():
    parsed_table = {
        "rows": [
            {"Distrito": "F District 10C"},
        ]
    }

    assert DriveService.guess_primary_district(parsed_table) == "District 10C"


def test_guess_primary_district_ignores_rows_without_digits():
    parsed_table = {
        "rows": [
            {"Distrito": "Prefijo F"},
            {"Distrito": "District 7A"},
        ]
    }

    assert DriveService.guess_primary_district(parsed_table) == "District 7A"


def test_generate_unique_filename_returns_original_when_available(drive_service):
    drive_service._service.files.return_value = _files_service({"20250110_doc.pdf"})

    name = drive_service._generate_unique_filename("folder123", "20250110_Distrito_doc.pdf")

    assert name == "20250110_Distrito_doc.pdf"


@pytest.mark.usefixtures("drive_service")
def test_generate_unique_filename_appends_timestamp(monkeypatch, drive_service):
    drive_service._service.files.return_value = _files_service({"20250110_Distrito_doc.pdf"})

    class FixedDatetime:
        @classmethod
        def utcnow(cls):
            return SimpleNamespace(strftime=lambda fmt: "20250102030405")

    monkeypatch.setattr("app.services.drive_service.datetime", FixedDatetime)

    name = drive_service._generate_unique_filename("folder123", "20250110_Distrito_doc.pdf")

    assert name.startswith("20250110_Distrito_doc_20250102030405")
    assert len(name) <= drive_service.MAX_FILENAME_LENGTH


def test_set_oauth_credentials_resets_client(drive_service):
    dummy_creds = SimpleNamespace(valid=True, expired=False)
    drive_service._service = MagicMock()

    drive_service.set_oauth_credentials(dummy_creds)

    assert drive_service._oauth_credentials == dummy_creds
    assert drive_service._service is None


def test_upload_attachments_handles_quota_error(drive_service):
    drive_service.ensure_generation_folder = MagicMock(return_value="folder123")

    quota_error = HttpError(
        resp=SimpleNamespace(status=403, reason="quotaExceeded", headers={}),
        content=b"Quota exceeded",
    )

    drive_service.upload_file = MagicMock(side_effect=quota_error)

    attachment = SimpleNamespace(
        filename="informe.pdf",
        content_type="application/pdf",
        data=b"PDFDATA",
    )

    folder_id, uploaded, errors = drive_service.upload_attachments("20250110", [attachment])

    assert folder_id == "folder123"
    assert uploaded == []
    assert len(errors) == 1
    assert errors[0]["code"] == "drive_upload_failed"
    assert "quota" in errors[0]["message"].lower()


def test_upload_attachments_generates_unique_names_for_duplicates(monkeypatch, drive_service):
    drive_service.ensure_generation_folder = MagicMock(return_value="folder123")

    files_mock = MagicMock()

    existing_initial = [{"name": "20250110_Distrito_doc.pdf"}]
    existing_after_first = [
        {"name": "20250110_Distrito_doc.pdf"},
        {"name": "20250110_Distrito_doc_20250102030405.pdf"},
    ]

    files_mock.list.side_effect = [
        SimpleNamespace(execute=lambda: {"files": existing_initial}),
        SimpleNamespace(execute=lambda: {"files": existing_after_first}),
    ]

    drive_service._service.files.return_value = files_mock

    class FixedDatetime:
        @classmethod
        def utcnow(cls):
            return SimpleNamespace(strftime=lambda fmt: "20250102030405")

    monkeypatch.setattr("app.services.drive_service.datetime", FixedDatetime)

    captured_names = []

    def fake_upload_file(*, filename, mime_type, data, parent_folder_id):
        captured_names.append(filename)
        return {
            "id": f"id_{len(captured_names)}",
            "name": filename,
            "webViewLink": f"view_{len(captured_names)}",
            "webContentLink": f"download_{len(captured_names)}",
        }

    drive_service.upload_file = MagicMock(side_effect=fake_upload_file)

    attachments = [
        SimpleNamespace(filename="doc.pdf", content_type="application/pdf", data=b"A"),
        SimpleNamespace(filename="doc.pdf", content_type="application/pdf", data=b"B"),
    ]

    folder_id, uploaded, errors = drive_service.upload_attachments(
        "20250110", attachments, distrito="Distrito"
    )

    assert folder_id == "folder123"
    assert errors == []
    assert captured_names == [
        "20250110_Distrito_doc_20250102030405.pdf",
        "20250110_Distrito_doc_20250102030405_1.pdf",
    ]
    assert [item["name"] for item in uploaded] == captured_names
