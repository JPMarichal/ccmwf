"""Cliente HTTP para enviar mensajes a Telegram.

Este módulo implementa la capa de acceso a la API de Telegram requerida por la
Fase 6. El enfoque sigue las reglas de logging (mensajes en español y campos
obligatorios) y retorna métricas estructuradas para su consumo por servicios de
negocio.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
import structlog

from ..logging_utils import bind_log_context, ensure_log_context


@dataclass(frozen=True)
class TelegramSendResult:
    """Resultado de una operación de envío a Telegram."""

    success: bool
    telegram_message_id: Optional[int]
    records_sent: int
    status_code: int
    duration_ms: int
    should_retry: bool
    error_code: Optional[str]
    error_description: Optional[str]
    raw_response: Optional[Dict[str, Any]]


class TelegramClient:
    """Cliente síncrono para la API `sendMessage` de Telegram."""

    _BASE_URL = "https://api.telegram.org"

    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        enabled: bool = True,
        timeout_seconds: int = 15,
        transport: Optional[httpx.BaseTransport] = None,
        logger: Optional[structlog.stdlib.BoundLogger] = None,
    ) -> None:
        if enabled:
            if not bot_token:
                raise ValueError("Se requiere bot_token para inicializar TelegramClient")
            if not chat_id:
                raise ValueError("Se requiere chat_id para inicializar TelegramClient")

        self._bot_token = bot_token
        self._chat_id = chat_id
        self._enabled = enabled
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._logger = logger or structlog.get_logger("telegram_service")
        self._send_endpoint = f"/bot{self._bot_token}/sendMessage" if self._bot_token else ""

    @property
    def enabled(self) -> bool:
        """Indica si el cliente tiene habilitadas las notificaciones."""

        return self._enabled

    @property
    def chat_id(self) -> str:
        """Chat o canal configurado para los envíos."""

        return self._chat_id

    def send_message(
        self,
        *,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
        message_id: Optional[str] = None,
    ) -> TelegramSendResult:
        """Envía un mensaje al chat configurado y retorna métricas estructuradas."""

        correlation_id = message_id or self._generate_correlation_id()
        context = ensure_log_context(
            etapa="fase_6_telegram",
            message_id=correlation_id,
            telegram_chat_id=self._chat_id,
        )
        logger = bind_log_context(self._logger, context)

        if not self._enabled:
            logger.warning(
                "Las notificaciones de Telegram están deshabilitadas",
                records_processed=0,
                records_skipped=1,
                error_code="telegram_disabled",
            )
            return TelegramSendResult(
                success=False,
                telegram_message_id=None,
                records_sent=0,
                status_code=0,
                duration_ms=0,
                should_retry=False,
                error_code="telegram_disabled",
                error_description="Las notificaciones de Telegram están deshabilitadas.",
                raw_response=None,
            )

        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }

        start_time = time.perf_counter()
        try:
            with httpx.Client(
                base_url=self._BASE_URL,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(self._send_endpoint, json=payload)
        except httpx.TimeoutException as exc:
            duration_ms = self._elapsed_ms(start_time)
            logger.error(
                "Timeout al enviar mensaje a Telegram",
                error_code="telegram_timeout",
                duration_ms=duration_ms,
                records_processed=0,
                records_skipped=1,
                exception=str(exc),
            )
            return TelegramSendResult(
                success=False,
                telegram_message_id=None,
                records_sent=0,
                status_code=0,
                duration_ms=duration_ms,
                should_retry=True,
                error_code="telegram_timeout",
                error_description="La solicitud a Telegram excedió el tiempo máximo permitido.",
                raw_response=None,
            )
        except httpx.HTTPError as exc:
            duration_ms = self._elapsed_ms(start_time)
            logger.error(
                "Error HTTP al enviar mensaje a Telegram",
                error_code="telegram_http_error",
                duration_ms=duration_ms,
                records_processed=0,
                records_skipped=1,
                exception=str(exc),
            )
            return TelegramSendResult(
                success=False,
                telegram_message_id=None,
                records_sent=0,
                status_code=0,
                duration_ms=duration_ms,
                should_retry=True,
                error_code="telegram_http_error",
                error_description="Error HTTP al comunicarse con Telegram.",
                raw_response=None,
            )

        duration_ms = self._elapsed_ms(start_time)

        if response.status_code != 200:
            logger.error(
                "Telegram respondió con un código HTTP inesperado",
                telegram_response_code=response.status_code,
                error_code="telegram_unexpected_status",
                duration_ms=duration_ms,
                records_processed=0,
                records_skipped=1,
            )
            return TelegramSendResult(
                success=False,
                telegram_message_id=None,
                records_sent=0,
                status_code=response.status_code,
                duration_ms=duration_ms,
                should_retry=response.status_code >= 500,
                error_code="telegram_unexpected_status",
                error_description="Telegram respondió con un código HTTP inesperado.",
                raw_response=self._safe_json(response),
            )

        data = self._safe_json(response)
        if not data:
            logger.error(
                "Telegram respondió sin cuerpo JSON válido",
                telegram_response_code=response.status_code,
                error_code="telegram_empty_body",
                duration_ms=duration_ms,
                records_processed=0,
                records_skipped=1,
            )
            return TelegramSendResult(
                success=False,
                telegram_message_id=None,
                records_sent=0,
                status_code=response.status_code,
                duration_ms=duration_ms,
                should_retry=True,
                error_code="telegram_empty_body",
                error_description="No se recibió un cuerpo JSON válido desde Telegram.",
                raw_response=None,
            )

        if data.get("ok"):
            telegram_message_id = self._extract_message_id(data)
            logger.info(
                "Mensaje enviado exitosamente a Telegram",
                telegram_response_code=response.status_code,
                telegram_message_id=telegram_message_id,
                duration_ms=duration_ms,
                records_processed=1,
                records_skipped=0,
            )
            return TelegramSendResult(
                success=True,
                telegram_message_id=telegram_message_id,
                records_sent=1,
                status_code=response.status_code,
                duration_ms=duration_ms,
                should_retry=False,
                error_code=None,
                error_description=None,
                raw_response=data,
            )

        error_description = data.get("description", "Error no especificado por Telegram")
        api_error_code = data.get("error_code")
        logger.error(
            "Telegram reportó un error en la API",
            telegram_response_code=response.status_code,
            telegram_api_code=api_error_code,
            error_code="telegram_api_error",
            error_description=error_description,
            duration_ms=duration_ms,
            records_processed=0,
            records_skipped=1,
        )
        return TelegramSendResult(
            success=False,
            telegram_message_id=None,
            records_sent=0,
            status_code=response.status_code,
            duration_ms=duration_ms,
            should_retry=self._should_retry(api_error_code),
            error_code="telegram_api_error",
            error_description=error_description,
            raw_response=data,
        )

    @staticmethod
    def _generate_correlation_id() -> str:
        return str(int(time.time() * 1_000_000))

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)

    @staticmethod
    def _extract_message_id(data: Dict[str, Any]) -> Optional[int]:
        try:
            result = data.get("result")
            if isinstance(result, dict):
                msg_id = result.get("message_id")
                if isinstance(msg_id, int):
                    return msg_id
        except Exception:  # noqa: BLE001 - fallback seguro
            return None
        return None

    @staticmethod
    def _safe_json(response: httpx.Response) -> Optional[Dict[str, Any]]:
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                return parsed
            return None
        except ValueError:
            return None

    @staticmethod
    def _should_retry(api_error_code: Optional[int]) -> bool:
        if api_error_code is None:
            return True
        return api_error_code in {429, 500, 502, 503, 504}
