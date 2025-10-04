"""Pruebas de integración ligeras para los endpoints Telegram."""

from __future__ import annotations

from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_telegram_service, telegram_notification_service
from app.services.telegram_notification_service import TelegramNotificationResult, TelegramNotificationService


class DummyTelegramService(TelegramNotificationService):
    """Servicio de reemplazo que retorna resultados predefinidos."""

    def __init__(self) -> None:  # type: ignore[super-init-not-called]
        self.calls: Dict[str, Dict[str, object]] = {}
        self._next_result: Optional[TelegramNotificationResult] = None

    def set_next_result(self, result: TelegramNotificationResult) -> None:
        self._next_result = result

    def _capture(self, name: str, params: Dict[str, object]) -> None:
        self.calls[name] = params

    def send_upcoming_arrivals(self, **kwargs) -> TelegramNotificationResult:  # type: ignore[override]
        self._capture("send_upcoming_arrivals", kwargs)
        assert self._next_result is not None
        return self._next_result

    def send_upcoming_birthdays(self, **kwargs) -> TelegramNotificationResult:  # type: ignore[override]
        self._capture("send_upcoming_birthdays", kwargs)
        assert self._next_result is not None
        return self._next_result

    def send_alert(self, **kwargs) -> TelegramNotificationResult:  # type: ignore[override]
        self._capture("send_alert", kwargs)
        assert self._next_result is not None
        return self._next_result


@pytest.fixture()
def client() -> TestClient:
    dummy_service = DummyTelegramService()

    global telegram_notification_service  # type: ignore[global-variable-not-assigned]
    original_global = telegram_notification_service
    telegram_notification_service = dummy_service

    original_override = app.dependency_overrides.get(get_telegram_service)
    app.dependency_overrides[get_telegram_service] = lambda: dummy_service

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        telegram_notification_service = original_global
        if original_override is not None:
            app.dependency_overrides[get_telegram_service] = original_override
        else:
            app.dependency_overrides.pop(get_telegram_service, None)


def _result_stub(dataset_id: str = "upcoming_arrivals") -> TelegramNotificationResult:
    return TelegramNotificationResult(
        success=True,
        telegram_message_id=999,
        records_sent=1,
        status_code=200,
        duration_ms=150,
        dataset_id=dataset_id,
        dataset_records=3,
        dataset_duration_ms=120,
        message_id="test-msg",
        error_code=None,
        error_description=None,
        raw_response={"ok": True},
    )


def test_endpoint_proximos_ingresos(client: TestClient) -> None:
    service: DummyTelegramService = telegram_notification_service  # type: ignore[assignment]
    service.set_next_result(_result_stub("upcoming_arrivals"))

    payload = {"branch_id": 14, "force_refresh": True, "days_ahead": 45}
    response = client.post("/telegram/proximos-ingresos", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert service.calls["send_upcoming_arrivals"]["branch_id"] == 14
    assert service.calls["send_upcoming_arrivals"]["force_refresh"] is True


def test_endpoint_proximos_cumpleanos(client: TestClient) -> None:
    service: DummyTelegramService = telegram_notification_service  # type: ignore[assignment]
    service.set_next_result(_result_stub("upcoming_birthdays"))

    payload = {"branch_id": None, "force_refresh": False, "days_ahead": 120}
    response = client.post("/telegram/proximos-cumpleanos", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "upcoming_birthdays"
    assert service.calls["send_upcoming_birthdays"]["days_ahead"] == 120


def test_endpoint_alerta(client: TestClient) -> None:
    service: DummyTelegramService = telegram_notification_service  # type: ignore[assignment]
    service.set_next_result(_result_stub("alert"))

    payload = {"title": "Sistema", "body": "Todo en orden", "level": "info"}
    response = client.post("/telegram/alerta", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "alert"
    assert service.calls["send_alert"]["title"] == "Sistema"
