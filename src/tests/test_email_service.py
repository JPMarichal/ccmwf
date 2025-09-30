"""
Tests para el Email Service y componentes relacionados.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

import pytest
from fastapi.testclient import TestClient

from app.main import app

from app.config import Settings
from app.models import EmailAttachment, ProcessingResult
from app.services.email_service import EmailService
from app.services.validators import validate_email_structure


@pytest.fixture
def imap_settings():
    """Configuración base para escenarios IMAP."""
    return Settings(
        _env_file=None,
        gmail_user="test@example.com",
        gmail_app_password="test-password",
        email_subject_pattern="Misioneros que llegan",
        processed_label="test-processed",
        app_env="development",
        log_level="DEBUG"
    )


@pytest.fixture
def oauth_settings():
    """Configuración base para escenarios OAuth."""
    return Settings(
        _env_file=None,
        gmail_user="test@example.com",
        google_application_credentials="creds.json",
        google_token_path="token.pickle",
        email_subject_pattern="Misioneros que llegan",
        processed_label="test-processed",
        app_env="development",
        log_level="DEBUG"
    )


@pytest.fixture
def drive_service_mock():
    """Servicio de Drive simulado para validar interacción sin realizar subidas reales."""
    drive_service = Mock()
    drive_service.upload_attachments.return_value = (None, [], [])
    return drive_service


@pytest.fixture
def email_service(imap_settings, drive_service_mock):
    """Instancia de EmailService con configuración IMAP y Drive simulado."""
    return EmailService(imap_settings, drive_service=drive_service_mock)


@pytest.fixture
def sample_email():
    """Email de prueba con cuerpo y attachment."""
    msg = MIMEMultipart()
    msg['Subject'] = "Misioneros que llegan el 15 de enero"
    msg['From'] = "test@example.com"
    msg['Date'] = email.utils.formatdate()

    body = MIMEText("Generación del 15 de enero de 2025")
    msg.attach(body)

    html_body = MIMEText(
        """
        <html>
          <body>
            <p>Generación del 15 de enero de 2025</p>
            <table>
              <tr><th>Distrito</th><th>Zona</th></tr>
              <tr><td>15B</td><td>Benemerito</td></tr>
            </table>
          </body>
        </html>
        """,
        "html",
    )
    msg.attach(html_body)

    attachment = MIMEApplication(b"data", Name="info.pdf")
    attachment['Content-Disposition'] = 'attachment; filename="info.pdf"'
    msg.attach(attachment)

    return msg


class TestEmailService:
    """Tests para la clase EmailService."""

    def test_service_initialization(self, imap_settings, drive_service_mock):
        service = EmailService(imap_settings, drive_service=drive_service_mock)

        assert service.settings == imap_settings
        assert service.imap_client is None
        assert service._connected is False
        assert service.use_oauth is False
        assert service.drive_service is drive_service_mock

    def test_should_use_oauth(self, oauth_settings):
        drive_service = Mock()
        service = EmailService(oauth_settings, drive_service=drive_service)
        assert service.use_oauth is True

    def test_extract_fecha_generacion(self, email_service):
        body = "Generación del 15 de enero de 2025"
        fecha = email_service._extract_fecha_generacion(body)

        assert fecha == "20250115"

    def test_extract_fecha_no_encontrada(self, email_service):
        body = "Email sin fecha específica"
        fecha = email_service._extract_fecha_generacion(body)

        assert fecha is None

    def test_decode_header(self, email_service):
        header = "Misioneros que llegan"
        assert email_service._decode_header(header) == header

    def test_get_email_body_text(self, email_service):
        msg = MIMEText("Contenido plano")
        assert email_service._get_email_body(msg) == "Contenido plano"

    def test_get_email_body_multipart(self, email_service, sample_email):
        body = email_service._get_email_body(sample_email)
        assert "Generación del 15 de enero de 2025" in body

    def test_get_email_html(self, email_service, sample_email):
        html = email_service._get_email_html(sample_email)
        assert "<table>" in html

    @pytest.mark.asyncio
    async def test_process_single_imap_email_validation_errors(self, email_service):
        email_service.imap_client = Mock()
        email_service.imap_client.add_flags = Mock()
        email_service.imap_client.add_labels = Mock()

        msg = MIMEText("Contenido sin información relevante")
        msg['Subject'] = "Correo irrelevante"
        msg['From'] = "test@example.com"
        msg['Date'] = email.utils.formatdate()

        result = await email_service._process_single_imap_email(msg, 123)

        assert result['success'] is False
        assert 'validation_errors' in result
        assert 'subject_pattern_mismatch' in result['validation_errors']
        assert 'attachments_missing' in result['validation_errors']
        assert 'html_missing' in result['table_errors']

    @pytest.mark.asyncio
    async def test_process_single_imap_email_parses_html_table(self, email_service, sample_email, drive_service_mock):
        email_service.imap_client = Mock()
        email_service.imap_client.add_flags = Mock()
        email_service.imap_client.add_labels = Mock()
        drive_service_mock.upload_attachments.return_value = (
            "folder123",
            [{"id": "f1", "name": "20250115_15B_info.pdf", "webViewLink": "view", "webContentLink": "download"}],
            [],
        )

        result = await email_service._process_single_imap_email(sample_email, 456)

        assert result['success'] is True
        assert result['parsed_table']['headers'] == ['Distrito', 'Zona']
        assert result['parsed_table']['rows'][0]['Distrito'] == '15B'
        assert result['table_errors'] == []
        assert result['drive_folder_id'] == "folder123"
        assert len(result['drive_uploaded_files']) == 1
        assert result['drive_upload_errors'] == []
        drive_service_mock.upload_attachments.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_single_imap_email_table_missing_columns(self, email_service, drive_service_mock):
        email_service.imap_client = Mock()
        email_service.imap_client.add_flags = Mock()
        email_service.imap_client.add_labels = Mock()

        drive_service_mock.upload_attachments.return_value = ("folder123", [], [])

        msg = MIMEMultipart()
        msg['Subject'] = "Misioneros que llegan el 20 de enero"
        msg['From'] = "test@example.com"
        msg['Date'] = email.utils.formatdate()

        msg.attach(MIMEText("Generación del 20 de enero de 2025"))
        html_body = MIMEText(
            """
            <html><body>
              <table>
                <tr><th>Distrito</th></tr>
                <tr><td></td></tr>
              </table>
            </body></html>
            """,
            "html",
        )
        msg.attach(html_body)

        attachment = MIMEApplication(b"data", Name="info.pdf")
        attachment['Content-Disposition'] = 'attachment; filename="info.pdf"'
        msg.attach(attachment)

        result = await email_service._process_single_imap_email(msg, 789)

        assert result['success'] is False
        assert any(err.startswith('column_missing:') for err in result['table_errors'])
        assert any(err.startswith('value_missing:') for err in result['table_errors'])
        assert result['drive_folder_id'] == "folder123"
        assert result['drive_uploaded_files'] == []
        assert result['drive_upload_errors'] == []

    @pytest.mark.asyncio
    async def test_ensure_imap_connection_success(self, email_service):
        with patch("app.services.email_service.imapclient.IMAPClient") as mock_imap:
            mock_client = Mock()
            mock_imap.return_value = mock_client
            mock_client.login.return_value = None
            mock_client.enable.return_value = None

            await email_service._ensure_imap_connection()

            assert email_service._connected is True
            mock_imap.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_imap_connection_failure(self, email_service):
        with patch("app.services.email_service.imapclient.IMAPClient") as mock_imap:
            mock_client = Mock()
            mock_imap.return_value = mock_client
            mock_client.login.side_effect = Exception("Login failed")

            with pytest.raises(Exception):
                await email_service._ensure_imap_connection()

            assert email_service._connected is False

    @pytest.mark.asyncio
    async def test_close_connection(self, email_service):
        email_service.imap_client = Mock()
        email_service._connected = True

        await email_service.close()

        email_service.imap_client.logout.assert_called_once()
        assert email_service._connected is False

    @pytest.mark.asyncio
    async def test_process_incoming_emails_uses_oauth(self, oauth_settings):
        mock_result = ProcessingResult(
            success=True,
            processed=2,
            errors=0,
            details=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=0.5
        )

        with patch("app.services.email_service.GmailOAuthService") as mock_service_cls:
            gmail_service = AsyncMock()
            gmail_service.process_incoming_emails.return_value = mock_result
            mock_service_cls.return_value = gmail_service

            drive_service = Mock()
            service = EmailService(oauth_settings, drive_service=drive_service)
            result = await service.process_incoming_emails()

            gmail_service.process_incoming_emails.assert_awaited_once()
            assert result.success is True

    @pytest.mark.asyncio
    async def test_search_emails_uses_oauth(self, oauth_settings):
        with patch("app.services.email_service.GmailOAuthService") as mock_service_cls:
            gmail_service = AsyncMock()
            gmail_service.search_emails.return_value = [
                {"id": "1", "subject": "Test"}
            ]
            mock_service_cls.return_value = gmail_service

            drive_service = Mock()
            service = EmailService(oauth_settings, drive_service=drive_service)
            results = await service.search_emails("subject:Test")

            gmail_service.search_emails.assert_awaited_once_with("subject:Test")
            assert results[0]["subject"] == "Test"


class TestModels:
    """Tests básicos para los modelos Pydantic."""

    def test_email_attachment_creation(self):
        attachment = EmailAttachment(
            filename="file.pdf",
            size=100,
            content_type="application/pdf"
        )

        assert attachment.filename == "file.pdf"
        assert attachment.size == 100

    def test_processing_result_creation(self):
        result = ProcessingResult(
            success=True,
            processed=1,
            errors=0,
            details=[],
            start_time=datetime.now()
        )

        assert result.success is True
        assert result.errors == 0


class TestAPIEndpoints:
    """Tests para los endpoints FastAPI definidos en `app/main.py`."""

    @pytest.fixture(autouse=True)
    def clear_service_state(self):
        from app import main
        main.email_service = None
        yield
        main.email_service = None

    def test_health_endpoint(self):
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "email-service"

    def test_process_emails_endpoint(self):
        with patch("app.main.EmailService") as service_cls:
            service_instance = service_cls.return_value
            service_instance.test_connection = AsyncMock(return_value=True)
            service_instance.close = AsyncMock()
            service_instance.process_incoming_emails = AsyncMock(return_value=ProcessingResult(
                success=True,
                processed=1,
                errors=0,
                details=[],
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_seconds=0.1
            ))

            with TestClient(app) as client:
                response = client.post("/process-emails")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            service_instance.process_incoming_emails.assert_awaited_once()
            service_instance.close.assert_awaited()

    def test_process_emails_endpoint_without_service(self):
        with patch("app.main.EmailService") as service_cls:
            service_instance = service_cls.return_value
            service_instance.test_connection = AsyncMock(return_value=True)
            service_instance.close = AsyncMock()

            with TestClient(app) as client:
                from app import main
                main.email_service = None
                response = client.post("/process-emails")

        assert response.status_code == 500
        assert "no inicializado" in response.json()["detail"]

    def test_search_emails_endpoint(self):
        with patch("app.main.EmailService") as service_cls:
            service_instance = service_cls.return_value
            service_instance.test_connection = AsyncMock(return_value=True)
            service_instance.close = AsyncMock()
            service_instance.search_emails = AsyncMock(return_value=[{"id": "1", "subject": "Test"}])

            with TestClient(app) as client:
                response = client.get("/emails/search", params={"query": "subject:Test"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["emails"][0]["subject"] == "Test"
            service_instance.search_emails.assert_awaited_once_with("subject:Test")
            service_instance.close.assert_awaited()

    def test_search_emails_endpoint_without_service(self):
        with patch("app.main.EmailService") as service_cls:
            service_instance = service_cls.return_value
            service_instance.test_connection = AsyncMock(return_value=True)
            service_instance.close = AsyncMock()

            with TestClient(app) as client:
                from app import main
                main.email_service = None
                response = client.get("/emails/search")

        assert response.status_code == 500
        assert "no inicializado" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestValidators:
    """Tests for email structure validation helpers."""

    def test_validate_email_structure_success(self):
        attachments = [EmailAttachment(filename="info.pdf", size=10, content_type="application/pdf")]
        is_valid, errors = validate_email_structure(
            subject="Misioneros que llegan el 10 de enero",
            fecha_generacion="20250110",
            attachments=attachments,
            expected_subject_pattern="Misioneros que llegan"
        )

        assert is_valid is True
        assert errors == []

    def test_validate_email_structure_missing_parts(self):
        attachments = [EmailAttachment(filename="info.txt", size=10, content_type="text/plain")]
        is_valid, errors = validate_email_structure(
            subject="Correo irrelevante",
            fecha_generacion=None,
            attachments=attachments,
            expected_subject_pattern="Misioneros que llegan"
        )

        assert is_valid is False
        assert "subject_pattern_mismatch" in errors
        assert "fecha_generacion_missing" in errors
        assert "pdf_attachment_missing" in errors
