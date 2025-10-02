"""Pruebas de utilidades de logging.

Estas pruebas validan los requisitos de logging estructurado descritos en
`logging-rules.md`, asegurando que los campos obligatorios se propaguen.
"""

import sys
from pathlib import Path

import structlog
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app.logging_utils import MANDATORY_FIELDS, ensure_log_context, bind_log_context
from structlog.testing import capture_logs


@pytest.fixture(autouse=True)
def reset_structlog():
    """Restablece la configuración de structlog antes de cada prueba."""
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


def test_ensure_log_context_includes_mandatory_fields():
    """Verifica que `ensure_log_context` llena todos los campos obligatorios (req: logging-rules.md)."""
    base = {"message_id": "abc-123", "extra_field": "valor"}

    context = ensure_log_context(base, etapa="drive_upload", drive_folder_id="folder-01")

    for field in MANDATORY_FIELDS:
        assert field in context, f"El campo obligatorio {field} debe estar presente"

    assert context["message_id"] == "abc-123"
    assert context["etapa"] == "drive_upload"
    assert context["drive_folder_id"] == "folder-01"
    assert context["extra_field"] == "valor"
    assert context["records_processed"] is None


def test_bind_log_context_filters_none_and_binds():
    """Garantiza que `bind_log_context` adjunta campos obligatorios y omite valores `None`."""
    context = ensure_log_context(etapa="procesamiento", message_id="log-001")

    with capture_logs() as logs:
        logger = structlog.get_logger("email_service").bind(servicio="email_service")
        bound_logger = bind_log_context(logger, context, records_processed=5, records_skipped=None)
        bound_logger.info("Evento de prueba")

    assert logs, "Se esperaba al menos un evento registrado"
    event = logs[-1]
    assert event["event"] == "Evento de prueba"
    assert event["servicio"] == "email_service"
    assert event["message_id"] == "log-001"
    assert event["etapa"] == "procesamiento"
    assert event["records_processed"] == 5
    assert "records_skipped" not in event
