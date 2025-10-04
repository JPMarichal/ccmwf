"""Pruebas unitarias para `TelegramClient`."""

from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest
import structlog

from app.services.telegram_client import TelegramClient, TelegramSendResult


class DummyTransport(httpx.BaseTransport):
    """Transporte de prueba que devuelve una respuesta predecible."""

    def __init__(self, *, status_code: int, json_body: Dict[str, Any] | None, raise_for: Exception | None = None) -> None:
        self._status_code = status_code
        self._json_body = json_body
        self._raise_for = raise_for

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # noqa: D401
        if self._raise_for:
            raise self._raise_for

        content = b""
        headers = {}
        if self._json_body is not None:
            content = json.dumps(self._json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        return httpx.Response(
            status_code=self._status_code,
            headers=headers,
            content=content,
            request=request,
        )


@pytest.fixture(autouse=True)
def clean_structlog_context() -> None:
    """Resetea contexto para evitar fugas entre pruebas."""

    structlog.contextvars.clear_contextvars()


def _make_client(**overrides: Any) -> TelegramClient:
    defaults = {
        "bot_token": "TEST_TOKEN",
        "chat_id": "-100123456",
        "enabled": True,
        "timeout_seconds": 5,
        "logger": structlog.get_logger("test_logger"),
    }
    defaults.update(overrides)
    return TelegramClient(**defaults)


def test_send_message_disabled_returns_notice() -> None:
    """Valida que el cliente devuelve fallo controlado cuando está deshabilitado."""

    client = _make_client(enabled=False)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_disabled"
    assert result.should_retry is False
    assert result.records_sent == 0


def test_send_message_successful_flow() -> None:
    """Verifica que el cliente procesa un 200 OK con `ok=true`."""

    transport = DummyTransport(
        status_code=200,
        json_body={
            "ok": True,
            "result": {
                "message_id": 42,
            },
        },
    )
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is True
    assert result.telegram_message_id == 42
    assert result.records_sent == 1
    assert result.error_code is None
    assert result.should_retry is False


def test_send_message_timeout_error() -> None:
    """Confirma que un timeout genera código de error específico y reintento."""

    transport = DummyTransport(
        status_code=0,
        json_body=None,
        raise_for=httpx.TimeoutException("timeout"),
    )
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_timeout"
    assert result.should_retry is True


def test_send_message_http_error() -> None:
    """Confirma que un error HTTP genérico se maneja correctamente."""

    transport = DummyTransport(
        status_code=0,
        json_body=None,
        raise_for=httpx.HTTPError("error http"),
    )
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_http_error"
    assert result.should_retry is True


def test_send_message_unexpected_status() -> None:
    """Verifica manejo de códigos HTTP distintos a 200."""

    transport = DummyTransport(status_code=500, json_body={"ok": False})
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_unexpected_status"
    assert result.should_retry is True


def test_send_message_empty_body() -> None:
    """Verifica que un cuerpo vacío provoca error controlado."""

    transport = DummyTransport(status_code=200, json_body=None)
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_empty_body"
    assert result.should_retry is True


def test_send_message_api_error_should_retry_on_rate_limit() -> None:
    """Confirma reintento cuando Telegram reporta rate limit (429)."""

    transport = DummyTransport(
        status_code=200,
        json_body={
            "ok": False,
            "error_code": 429,
            "description": "Too Many Requests",
        },
    )
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_api_error"
    assert result.should_retry is True


def test_send_message_api_error_should_not_retry_on_client_issue() -> None:
    """Confirma que errores de cliente (400) no se marcan para reintento."""

    transport = DummyTransport(
        status_code=200,
        json_body={
            "ok": False,
            "error_code": 400,
            "description": "Bad Request",
        },
    )
    client = _make_client(transport=transport)

    result = client.send_message(text="Hola")

    assert result.success is False
    assert result.error_code == "telegram_api_error"
    assert result.should_retry is False
