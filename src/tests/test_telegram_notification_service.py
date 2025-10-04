"""Pruebas unitarias para `TelegramNotificationService`."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest

from app.models import ReportDatasetMetadata, ReportDatasetResult
from app.services.report_preparation_service import DatasetValidationError
from app.services.telegram_client import TelegramSendResult
from app.services.telegram_notification_service import (
    TelegramNotificationResult,
    TelegramNotificationService,
)


def _build_metadata(
    *,
    dataset_id: str,
    record_count: int,
    branch_id: Optional[int] = 14,
    message_id: Optional[str] = None,
) -> ReportDatasetMetadata:
    return ReportDatasetMetadata(
        dataset_id=dataset_id,
        generated_at=datetime.utcnow(),
        record_count=record_count,
        branch_id=branch_id,
        duration_ms=123,
        message_id=message_id or "msg-001",
    )


class StubReportPreparationService:
    """Servicio stub que permite configurar resultados o excepciones por dataset."""

    def __init__(self) -> None:
        self.calls: Dict[str, int] = {}
        self._results: Dict[str, ReportDatasetResult] = {}
        self._exceptions: Dict[str, Exception] = {}
        self.default_branch_id = 14

    def set_result(self, dataset: str, result: ReportDatasetResult) -> None:
        self._results[dataset] = result

    def set_exception(self, dataset: str, exc: Exception) -> None:
        self._exceptions[dataset] = exc

    def prepare_upcoming_arrivals(self, **kwargs: Any) -> ReportDatasetResult:
        self.calls.setdefault("upcoming_arrivals", 0)
        self.calls["upcoming_arrivals"] += 1
        if "upcoming_arrivals" in self._exceptions:
            raise self._exceptions["upcoming_arrivals"]
        return self._results["upcoming_arrivals"]

    def prepare_upcoming_birthdays(self, **kwargs: Any) -> ReportDatasetResult:
        self.calls.setdefault("upcoming_birthdays", 0)
        self.calls["upcoming_birthdays"] += 1
        if "upcoming_birthdays" in self._exceptions:
            raise self._exceptions["upcoming_birthdays"]
        return self._results["upcoming_birthdays"]


class StubTelegramClient:
    """Cliente Telegram stub que captura mensajes enviados."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.chat_id = "-100123"
        self.messages: List[Dict[str, Any]] = []
        self._responses: List[TelegramSendResult] = []

    def queue_response(self, response: TelegramSendResult) -> None:
        self._responses.append(response)

    def send_message(self, *, text: str, message_id: Optional[str] = None, **kwargs: Any) -> TelegramSendResult:
        self.messages.append({"text": text, "message_id": message_id})
        if self._responses:
            return self._responses.pop(0)
        return TelegramSendResult(
            success=True,
            telegram_message_id=101,
            records_sent=1,
            status_code=200,
            duration_ms=120,
            should_retry=False,
            error_code=None,
            error_description=None,
            raw_response={"ok": True},
        )


@pytest.fixture
def stub_service() -> StubReportPreparationService:
    return StubReportPreparationService()


@pytest.fixture
def stub_client() -> StubTelegramClient:
    return StubTelegramClient()


@pytest.fixture
def notification_service(
    stub_service: StubReportPreparationService,
    stub_client: StubTelegramClient,
) -> TelegramNotificationService:
    return TelegramNotificationService(
        report_service=stub_service,
        telegram_client=stub_client,
        max_attempts=3,
        initial_backoff_seconds=0.01,
    )


def test_send_upcoming_arrivals_success(notification_service: TelegramNotificationService, stub_service: StubReportPreparationService, stub_client: StubTelegramClient) -> None:
    """Debe enviar un mensaje con el formato esperado para próximos ingresos."""

    metadata = _build_metadata(dataset_id="upcoming_arrivals", record_count=2, message_id="msg-arrivals")
    dataset_result = ReportDatasetResult(
        metadata=metadata,
        data=[
            {
                "district": "14A",
                "rdistrict": "Distrito Alfa",
                "branch_id": 14,
                "arrival_date": date.today() + timedelta(days=6),
                "departure_date": date.today() + timedelta(days=48),
                "missionaries_count": 5,
                "duration_weeks": 6,
            },
            {
                "district": "14B",
                "rdistrict": "Distrito Beta",
                "branch_id": 14,
                "arrival_date": date.today() + timedelta(days=6),
                "departure_date": date.today() + timedelta(days=48),
                "missionaries_count": 3,
                "duration_weeks": 6,
            },
        ],
    )
    stub_service.set_result("upcoming_arrivals", dataset_result)

    result = notification_service.send_upcoming_arrivals()

    assert result.success is True
    assert result.records_sent == 1
    assert stub_service.calls["upcoming_arrivals"] == 1
    assert "Próximos Ingresos" in stub_client.messages[0]["text"]
    assert "Distrito 14A" in stub_client.messages[0]["text"]


def test_send_upcoming_arrivals_empty_dataset(notification_service: TelegramNotificationService, stub_service: StubReportPreparationService, stub_client: StubTelegramClient) -> None:
    """Cuando el dataset está vacío se envía mensaje positivo informativo."""

    metadata = _build_metadata(dataset_id="upcoming_arrivals", record_count=0, message_id="empty")
    dataset_result = ReportDatasetResult(metadata=metadata, data=[])
    stub_service.set_result("upcoming_arrivals", dataset_result)

    result = notification_service.send_upcoming_arrivals()

    assert result.success is True
    assert "No hay misioneros" in stub_client.messages[0]["text"]


def test_send_upcoming_birthdays_groups_by_month(notification_service: TelegramNotificationService, stub_service: StubReportPreparationService, stub_client: StubTelegramClient) -> None:
    """Verifica que los cumpleaños se agrupen por mes y día."""

    today = date.today()
    metadata = _build_metadata(dataset_id="upcoming_birthdays", record_count=2, message_id="bday")
    dataset_result = ReportDatasetResult(
        metadata=metadata,
        data=[
            {
                "missionary_id": 1,
                "missionary_name": "Elder Hatcher",
                "treatment": "Elder Hatcher",
                "birthday": today.replace(month=11, day=5),
                "age_turning": 20,
                "status": "CCM",
            },
            {
                "missionary_id": 2,
                "missionary_name": "Hermana Perez",
                "treatment": "Hermana Perez",
                "birthday": today.replace(month=11, day=6),
                "age_turning": 21,
                "status": "Virtual",
            },
        ],
    )
    stub_service.set_result("upcoming_birthdays", dataset_result)

    result = notification_service.send_upcoming_birthdays()

    assert result.success is True
    message = stub_client.messages[0]["text"]
    assert "PRÓXIMOS CUMPLEAÑOS" in message
    assert "NOVIEMBRE" in message
    assert "05" in message and "06" in message


def test_client_disabled_short_circuits(stub_service: StubReportPreparationService, stub_client: StubTelegramClient) -> None:
    """Si el cliente está deshabilitado no se consulta el dataset."""

    stub_client.enabled = False
    notification_service = TelegramNotificationService(
        report_service=stub_service,
        telegram_client=stub_client,
    )
    result = notification_service.send_upcoming_arrivals()

    assert result.success is False
    assert stub_service.calls.get("upcoming_arrivals", 0) == 0
    assert result.error_code == "telegram_disabled"


def test_dataset_validation_error(notification_service: TelegramNotificationService, stub_service: StubReportPreparationService) -> None:
    """Los errores de validación deben propagarse en el resultado."""

    stub_service.set_exception("upcoming_arrivals", DatasetValidationError("boom", error_code="invalid"))
    result = notification_service.send_upcoming_arrivals()

    assert result.success is False
    assert result.error_code == "invalid"
    assert result.error_description == "boom"


def test_send_with_retries_until_success(stub_service: StubReportPreparationService) -> None:
    """Debe reintentar ante respuestas con `should_retry=True`."""

    metadata = _build_metadata(dataset_id="upcoming_arrivals", record_count=1, message_id="retry")
    dataset_result = ReportDatasetResult(
        metadata=metadata,
        data=[
            {
                "district": "14A",
                "rdistrict": "Distrito Alpha",
                "branch_id": 14,
                "arrival_date": date.today() + timedelta(days=10),
                "departure_date": date.today() + timedelta(days=40),
                "missionaries_count": 4,
                "duration_weeks": 6,
            }
        ],
    )
    stub_service.set_result("upcoming_arrivals", dataset_result)

    client = StubTelegramClient()
    client.queue_response(
        TelegramSendResult(
            success=False,
            telegram_message_id=None,
            records_sent=0,
            status_code=500,
            duration_ms=200,
            should_retry=True,
            error_code="telegram_api_error",
            error_description="too many requests",
            raw_response={"ok": False},
        )
    )
    client.queue_response(
        TelegramSendResult(
            success=True,
            telegram_message_id=999,
            records_sent=1,
            status_code=200,
            duration_ms=100,
            should_retry=False,
            error_code=None,
            error_description=None,
            raw_response={"ok": True},
        )
    )

    service = TelegramNotificationService(
        report_service=stub_service,
        telegram_client=client,
        max_attempts=3,
        initial_backoff_seconds=0.01,
    )

    result = service.send_upcoming_arrivals()

    assert result.success is True
    assert len(client.messages) == 2
    assert client.messages[-1]["message_id"] == "retry"


def test_empty_birthdays_uses_footer(notification_service: TelegramNotificationService, stub_service: StubReportPreparationService, stub_client: StubTelegramClient) -> None:
    """Cuando no hay cumpleaños el mensaje debe incluir el footer estándar."""

    metadata = _build_metadata(dataset_id="upcoming_birthdays", record_count=0, message_id="bday-empty")
    dataset_result = ReportDatasetResult(metadata=metadata, data=[])
    stub_service.set_result("upcoming_birthdays", dataset_result)

    result = notification_service.send_upcoming_birthdays()

    assert result.success is True
    message = stub_client.messages[0]["text"]
    assert "Rama" in message
    assert message.endswith("CCM Sistema")


def test_alert_formatting_uses_level_icon(notification_service: TelegramNotificationService, stub_client: StubTelegramClient) -> None:
    """Las alertas deben respetar el ícono según severidad."""

    result = notification_service.send_alert(title="Sistema", body="Todo en orden", level="warning")

    assert result.success is True
    message = stub_client.messages[0]["text"]
    assert message.startswith("⚠️")
    assert "Todo en orden" in message
    assert message.endswith("CCM Sistema")
