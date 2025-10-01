"""Tests for `DriveService` helpers and unique filename logic."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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
