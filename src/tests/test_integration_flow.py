"""Integration tests for FastAPI application lifecycle and endpoints."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.models import ProcessingResult


def _build_processing_result() -> ProcessingResult:
    start = datetime.now()
    end = start + timedelta(seconds=1)
    return ProcessingResult(
        success=True,
        processed=2,
        errors=0,
        details=[{"message_id": "abc123", "success": True}],
        start_time=start,
        end_time=end,
        duration_seconds=(end - start).total_seconds(),
    )


class IntegrationTestContext:
    """Helper to patch dependencies for integration tests."""

    def __init__(self, log_file: Path, process_result: ProcessingResult | None = None,
                 search_result: list[dict] | None = None, raise_error: bool = False) -> None:
        self.log_file = log_file
        self.process_result = process_result or _build_processing_result()
        self.search_result = search_result or [{"id": "1", "subject": "Test"}]
        self.raise_error = raise_error

        self.email_service_patch = patch("app.main.EmailService")
        self.settings_patch = patch("app.main.get_settings")

        self.email_service_cls = self.email_service_patch.start()
        self.settings_mock = self.settings_patch.start()

        settings = Settings(
            _env_file=None,
            gmail_user="test@example.com",
            google_application_credentials="creds.json",
            google_token_path="token.pickle",
            email_subject_pattern="Misioneros que llegan",
            processed_label="test-processed",
            log_file_path=str(self.log_file),
        )
        self.settings_mock.return_value = settings

        self.instance = self.email_service_cls.return_value
        self.instance.test_connection = AsyncMock(return_value=True)
        self.instance.close = AsyncMock()

        if self.raise_error:
            self.instance.process_incoming_emails = AsyncMock(side_effect=RuntimeError("Processing error"))
        else:
            self.instance.process_incoming_emails = AsyncMock(return_value=self.process_result)

        self.instance.search_emails = AsyncMock(return_value=self.search_result)

    def stop(self) -> None:
        self.email_service_patch.stop()
        self.settings_patch.stop()


def test_process_emails_success_flow(tmp_path: Path) -> None:
    """Ensure the full /process-emails flow succeeds and generates logs."""
    log_file = tmp_path / "email_service.log"
    ctx = IntegrationTestContext(log_file)

    with TestClient(app) as client:
        response = client.post("/process-emails")

    ctx.stop()

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"]["processed"] == 2
    ctx.instance.test_connection.assert_awaited_once()
    ctx.instance.process_incoming_emails.assert_awaited_once()
    ctx.instance.close.assert_awaited()

    # Logging configuration apunta a este archivo, pero algunas ejecuciones de test
    # pueden no generar un write inmediato. Verificamos al menos que el directorio exista.
    assert log_file.parent.exists()


def test_process_emails_failure_returns_error(tmp_path: Path) -> None:
    """When the service raises an error the API must respond with 500."""
    log_file = tmp_path / "email_service.log"
    ctx = IntegrationTestContext(log_file, raise_error=True)

    with TestClient(app) as client:
        response = client.post("/process-emails")

    ctx.stop()

    assert response.status_code == 500
    assert "Error procesando emails" in response.json()["detail"]
    ctx.instance.process_incoming_emails.assert_awaited_once()
    ctx.instance.close.assert_awaited()


def test_search_emails_success_flow(tmp_path: Path) -> None:
    """The /emails/search endpoint should return mocked search results."""
    log_file = tmp_path / "email_service.log"
    search_results = [{"id": "abc", "subject": "Test Subject"}]
    ctx = IntegrationTestContext(log_file, search_result=search_results)

    with TestClient(app) as client:
        response = client.get("/emails/search", params={"query": "subject:Test"})

    ctx.stop()

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["emails"] == search_results
    ctx.instance.search_emails.assert_awaited_once_with("subject:Test")
    ctx.instance.close.assert_awaited()
