"""Tests for `GmailOAuthService` covering OAuth-driven flows."""

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from googleapiclient.errors import HttpError

from app.config import Settings
from app.services.gmail_oauth_service import GmailOAuthService


def _build_settings(**overrides) -> Settings:
    data = {
        "gmail_user": "test@example.com",
        "google_application_credentials": "creds.json",
        "google_token_path": "token.pickle",
        "email_subject_pattern": "Misioneros que llegan",
        "processed_label": "misioneros-procesados",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def _encode_body(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")


def _http_error(status: int, message: str) -> HttpError:
    resp = SimpleNamespace(status=status, reason=message, headers={})
    return HttpError(resp=resp, content=message.encode("utf-8"))


def _default_message_payload() -> dict:
    html_body = """
        <html>
          <body>
            <p>Generación del 10 de enero de 2025</p>
            <table>
              <tr><th>Distrito</th><th>Zona</th></tr>
              <tr><td>14A</td><td>Benemerito</td></tr>
            </table>
          </body>
        </html>
    """
    return {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Misioneros que llegan el 10 de enero"},
                {"name": "From", "value": "natalia@example.com"},
                {"name": "Date", "value": "2025-01-10T00:00:00+00:00"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _encode_body("Generación del 10 de enero de 2025")},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": _encode_body(html_body)},
                },
                {
                    "mimeType": "application/pdf",
                    "filename": "info.pdf",
                    "body": {"attachmentId": "att1"},
                    "partId": "part_1",
                },
            ],
        }
    }


def _setup_service(settings: Settings, drive_service: Mock | None = None) -> GmailOAuthService:
    service = GmailOAuthService(settings, drive_service=drive_service)
    service.authenticate = AsyncMock(return_value=True)
    service._authenticated = True
    return service


def _mock_chain() -> tuple[MagicMock, MagicMock, MagicMock]:
    gmail_service = MagicMock(name="gmail_service")
    users = gmail_service.users.return_value
    messages = users.messages.return_value
    labels = users.labels.return_value
    return gmail_service, messages, labels


@pytest.mark.asyncio
async def test_process_incoming_emails_success():
    settings = _build_settings()
    service = _setup_service(settings)
    gmail_service, messages, labels = _mock_chain()

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = _default_message_payload()
    attachments = messages.attachments.return_value
    attachments.get.return_value.execute.return_value = {"data": _encode_body("PDFDATA")}

    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()

    assert result.success is True
    assert result.processed == 1
    detail = result.details[0]
    assert detail["success"] is True
    assert detail["parsed_table"]["headers"] == ["Distrito", "Zona"]
    assert detail["parsed_table"]["rows"][0]["Distrito"] == "14A"
    assert detail["table_errors"] == []
    assert detail["drive_folder_id"] is None
    assert detail["drive_uploaded_files"] == []
    assert detail["drive_upload_errors"] == []
    messages.modify.assert_any_call(userId="me", id="msg1", body={"removeLabelIds": ["UNREAD"]})
    messages.modify.assert_any_call(userId="me", id="msg1", body={"addLabelIds": ["lbl123"]})


@pytest.mark.asyncio
async def test_process_incoming_emails_no_messages():
    service = _setup_service(_build_settings())
    gmail_service, messages, labels = _mock_chain()

    messages.list.return_value.execute.return_value = {"messages": []}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()
    assert result.success is True
    assert result.processed == 0


@pytest.mark.asyncio
async def test_process_incoming_emails_http_error():
    service = _setup_service(_build_settings())
    gmail_service, messages, _ = _mock_chain()

    messages.list.return_value.execute.side_effect = _http_error(500, "Boom")

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()
    assert result.success is False
    assert "Boom" in result.details[0]["error"]


@pytest.mark.asyncio
async def test_process_incoming_emails_attachment_error():
    service = _setup_service(_build_settings())
    gmail_service, messages, labels = _mock_chain()

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = _default_message_payload()
    messages.attachments.return_value.get.return_value.execute.side_effect = RuntimeError("attachment error")

    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()
    detail = result.details[0]
    assert detail["attachments_count"] == 0
    assert detail["success"] is False
    assert "parsed_table" in detail
    assert detail["drive_uploaded_files"] == []


@pytest.mark.asyncio
async def test_search_emails_success():
    service = _setup_service(_build_settings())
    gmail_service, messages, _ = _mock_chain()

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Misioneros"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Date", "value": "2025-01-10"},
            ],
            "parts": [],
        }
    }

    service.gmail_service = gmail_service

    results = await service.search_emails("subject:Test")
    assert len(results) == 1
    assert results[0]["subject"] == "Misioneros"


@pytest.mark.asyncio
async def test_search_emails_error_returns_empty():
    service = _setup_service(_build_settings())
    gmail_service, messages, _ = _mock_chain()

    messages.list.return_value.execute.side_effect = _http_error(500, "API error")

    service.gmail_service = gmail_service
    assert await service.search_emails("subject:Test") == []


@pytest.mark.asyncio
async def test_process_incoming_emails_html_missing_generates_error():
    settings = _build_settings()
    service = _setup_service(settings)
    gmail_service, messages, labels = _mock_chain()

    payload = _default_message_payload()
    # Remove HTML part to force error
    payload["payload"]["parts"] = [payload["payload"]["parts"][0]]

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = payload
    attachments = messages.attachments.return_value
    attachments.get.return_value.execute.return_value = {"data": _encode_body("PDFDATA")}

    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()

    detail = result.details[0]
    assert detail["parsed_table"] is None
    assert detail["success"] is False
    assert "html_missing" in detail["table_errors"]
    assert detail["drive_uploaded_files"] == []


@pytest.mark.asyncio
async def test_process_incoming_emails_uploads_to_drive():
    settings = _build_settings()
    drive_service = Mock()
    drive_service.upload_attachments.return_value = (
        "folder123",
        [{"id": "f1", "name": "20250110_14A_info.pdf", "webViewLink": "view", "webContentLink": "download"}],
        [],
    )

    service = _setup_service(settings, drive_service=drive_service)
    gmail_service, messages, labels = _mock_chain()

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = _default_message_payload()
    attachments = messages.attachments.return_value
    attachments.get.return_value.execute.return_value = {"data": _encode_body("PDFDATA")}

    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()

    detail = result.details[0]
    assert detail["drive_folder_id"] == "folder123"
    assert len(detail["drive_uploaded_files"]) == 1
    assert detail["drive_upload_errors"] == []
    drive_service.upload_attachments.assert_called_once()


@pytest.mark.asyncio
async def test_process_incoming_emails_drive_missing_fecha_generacion():
    settings = _build_settings()
    drive_service = Mock()
    drive_service.upload_attachments.return_value = ("folder123", [], [])

    service = _setup_service(settings, drive_service=drive_service)
    gmail_service, messages, labels = _mock_chain()

    payload = _default_message_payload()
    payload["payload"]["parts"][0]["body"]["data"] = _encode_body("Mensaje sin fecha")

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = payload
    attachments = messages.attachments.return_value
    attachments.get.return_value.execute.return_value = {"data": _encode_body("PDFDATA")}

    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()

    detail = result.details[0]
    assert detail["drive_folder_id"] is None
    assert detail["drive_uploaded_files"] == []
    assert any(err.get("code") == "drive_missing_fecha_generacion" for err in detail["drive_upload_errors"])
    drive_service.upload_attachments.assert_not_called()


@pytest.mark.asyncio
async def test_process_incoming_emails_column_missing_generates_error():
    settings = _build_settings()
    service = _setup_service(settings)
    gmail_service, messages, labels = _mock_chain()

    payload = _default_message_payload()
    # Modify table to keep required columns but leave Zona value empty
    payload["payload"]["parts"][1]["body"]["data"] = _encode_body(
        """
        <html><body>
        <table>
          <tr><th>Distrito</th><th>Zona</th></tr>
          <tr><td>15C</td><td></td></tr>
        </table>
        </body></html>
        """
    )

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = payload
    attachments = messages.attachments.return_value
    attachments.get.return_value.execute.return_value = {"data": _encode_body("PDFDATA")}

    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()

    detail = result.details[0]
    assert detail["success"] is False
    assert "value_missing:Zona:0" in detail["table_errors"]


@pytest.mark.asyncio
async def test_mark_message_processed_conflict():
    service = _setup_service(_build_settings())
    gmail_service, messages, labels = _mock_chain()

    labels.create.return_value.execute.side_effect = _http_error(409, "exists")
    labels.list.return_value.execute.return_value = {
        "labels": [{"id": "lbl123", "name": service.settings.processed_label}]
    }

    service.gmail_service = gmail_service

    await service._mark_message_processed("msg1")

    labels.list.return_value.execute.assert_called_once_with()
    messages.modify.assert_any_call(userId="me", id="msg1", body={"removeLabelIds": ["UNREAD"]})
    messages.modify.assert_any_call(userId="me", id="msg1", body={"addLabelIds": ["lbl123"]})


@pytest.mark.asyncio
async def test_mark_message_processed_without_label():
    service = _setup_service(_build_settings(processed_label=""))
    gmail_service, messages, _ = _mock_chain()

    service.gmail_service = gmail_service

    await service._mark_message_processed("msg1")

    messages.modify.assert_called_once_with(userId="me", id="msg1", body={"removeLabelIds": ["UNREAD"]})


def test_get_message_body_prefers_plain_text():
    payload = {
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _encode_body("Texto plano")}},
            {"mimeType": "text/html", "body": {"data": _encode_body("<p>HTML</p>")}},
        ]
    }
    service = GmailOAuthService(_build_settings())
    assert service._get_message_body(payload) == "Texto plano"


def test_get_message_body_prefers_html_when_no_text():
    payload = {
        "parts": [
            {"mimeType": "text/html", "body": {"data": _encode_body("<p>HTML</p>")}}
        ]
    }
    service = GmailOAuthService(_build_settings())
    assert "HTML" in service._get_message_body(payload)


def test_get_all_parts_recursive():
    payload = {
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _encode_body("text")}},
            {
                "mimeType": "multipart/mixed",
                "parts": [{"mimeType": "application/pdf", "body": {"data": _encode_body("pdf")}}],
            },
        ]
    }
    service = GmailOAuthService(_build_settings())
    assert len(service._get_all_parts(payload)) == 3


def test_get_attachment_data_error_returns_none():
    service = GmailOAuthService(_build_settings())
    gmail_service, messages, _ = _mock_chain()
    messages.attachments.return_value.get.return_value.execute.side_effect = RuntimeError("attachment error")
    service.gmail_service = gmail_service

    assert service._get_attachment_data("msg", "part") is None


def test_extract_fecha_generacion_cases():
    service = GmailOAuthService(_build_settings())
    assert service._extract_fecha_generacion("Mensaje sin fecha") is None
    assert service._extract_fecha_generacion("Generación del 5 de marzo de 2024") == "20240305"


def test_get_header_value_missing():
    service = GmailOAuthService(_build_settings())
    assert service._get_header_value([{"name": "Subject", "value": "Test"}], "From") == ""


@pytest.mark.asyncio
async def test_close_resets_state():
    service = GmailOAuthService(_build_settings())
    service.gmail_service = object()
    service.credentials = object()
    service._authenticated = True

    await service.close()

    assert service.gmail_service is None
    assert service.credentials is None
    assert service._authenticated is False
