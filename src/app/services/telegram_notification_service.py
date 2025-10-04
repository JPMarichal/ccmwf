"""Servicio de notificaciones por Telegram (Fase 6)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import structlog

from app.logging_utils import bind_log_context, ensure_log_context
from app.models import ReportDatasetResult
from app.services.report_preparation_service import (
    DatasetValidationError,
    ReportPreparationError,
    ReportPreparationService,
)
from app.services.telegram_client import TelegramClient, TelegramSendResult


@dataclass(frozen=True)
class TelegramNotificationResult:
    """Resultado de un envío realizado a través del servicio."""

    success: bool
    telegram_message_id: Optional[int]
    records_sent: int
    status_code: int
    duration_ms: int
    dataset_id: Optional[str]
    dataset_records: int
    dataset_duration_ms: Optional[int]
    message_id: str
    error_code: Optional[str]
    error_description: Optional[str]
    raw_response: Optional[Dict[str, object]]


class TelegramNotificationService:
    """Orquesta la generación y envío de reportes hacia Telegram."""

    def __init__(
        self,
        *,
        report_service: ReportPreparationService,
        telegram_client: TelegramClient,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 1.0,
    ) -> None:
        """Inicializa el orquestador de notificaciones hacia Telegram.

        Args:
            report_service: Fachada que provee los datasets (`UpcomingArrival`,
                `UpcomingBirthday`, etc.) reutilizados por las notificaciones.
            telegram_client: Cliente HTTP encargado de ejecutar los envíos hacia
                la API de Telegram. Debe tener configuradas las credenciales y
                el chat objetivo.
            max_attempts: Número máximo de intentos por mensaje cuando la API
                responde con condiciones recuperables. Se fuerza un mínimo de 1.
            initial_backoff_seconds: Intervalo inicial (en segundos) para la
                estrategia de backoff exponencial entre reintentos. Se fuerza un
                mínimo de 0.1 segundos.
        """
        self._report_service = report_service
        self._client = telegram_client
        self._max_attempts = max(1, max_attempts)
        self._initial_backoff_seconds = max(0.1, initial_backoff_seconds)
        self._logger = structlog.get_logger("telegram_service")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def send_upcoming_arrivals(
        self,
        *,
        branch_id: Optional[int] = None,
        force_refresh: bool = False,
        days_ahead: int = 60,
    ) -> TelegramNotificationResult:
        """Envía reporte de próximos ingresos al CCM."""

        return self._send_dataset_report(
            dataset_id="upcoming_arrivals",
            branch_id=branch_id,
            force_refresh=force_refresh,
            dataset_fetcher=lambda: self._report_service.prepare_upcoming_arrivals(
                branch_id=branch_id,
                force_refresh=force_refresh,
                days_ahead=days_ahead,
            ),
            formatter=self._format_upcoming_arrivals,
            empty_message="✅ No hay misioneros programados para ingresar al CCM en las próximas semanas.",
        )

    def send_upcoming_birthdays(
        self,
        *,
        branch_id: Optional[int] = None,
        force_refresh: bool = False,
        days_ahead: int = 90,
    ) -> TelegramNotificationResult:
        """Envía reporte de próximos cumpleaños."""

        return self._send_dataset_report(
            dataset_id="upcoming_birthdays",
            branch_id=branch_id,
            force_refresh=force_refresh,
            dataset_fetcher=lambda: self._report_service.prepare_upcoming_birthdays(
                branch_id=branch_id,
                force_refresh=force_refresh,
                days_ahead=days_ahead,
            ),
            formatter=self._format_upcoming_birthdays,
            empty_message="✅ No hay cumpleaños próximos programados para los próximos meses.",
        )

    def send_alert(
        self,
        *,
        title: str,
        body: str,
        level: str = "info",
        branch_id: Optional[int] = None,
    ) -> TelegramNotificationResult:
        """Envía una alerta operativa simple."""

        message_id = datetime.utcnow().strftime("alert%Y%m%d%H%M%S%f")
        context = ensure_log_context(
            etapa="fase_6_telegram",
            message_id=message_id,
            dataset_id="alert",
            telegram_chat_id=self._client.chat_id if self._client.chat_id else None,
            records_processed=0,
            records_skipped=0,
        )
        logger = bind_log_context(self._logger, context)

        logger.info("telegram_alert_started", title=title, level=level)

        text = self._format_alert(title=title, body=body, level=level, branch_id=branch_id)
        send_result = self._send_with_retries(text=text, message_id=message_id)

        log_event = "telegram_alert_completed" if send_result.success else "telegram_alert_error"
        logger.info(
            log_event,
            telegram_message_id=send_result.telegram_message_id,
            status_code=send_result.status_code,
            duration_ms=send_result.duration_ms,
            error_code=send_result.error_code,
        )

        return TelegramNotificationResult(
            success=send_result.success,
            telegram_message_id=send_result.telegram_message_id,
            records_sent=send_result.records_sent,
            status_code=send_result.status_code,
            duration_ms=send_result.duration_ms,
            dataset_id="alert",
            dataset_records=0,
            dataset_duration_ms=None,
            message_id=message_id,
            error_code=send_result.error_code,
            error_description=send_result.error_description,
            raw_response=send_result.raw_response,
        )

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------
    def _send_dataset_report(
        self,
        *,
        dataset_id: str,
        branch_id: Optional[int],
        force_refresh: bool,
        dataset_fetcher: Callable[[], ReportDatasetResult],
        formatter: Callable[[ReportDatasetResult], str],
        empty_message: str,
    ) -> TelegramNotificationResult:
        if not self._client.enabled:
            disabled_result = TelegramSendResult(
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
            return TelegramNotificationResult(
                success=False,
                telegram_message_id=None,
                records_sent=0,
                status_code=0,
                duration_ms=0,
                dataset_id=dataset_id,
                dataset_records=0,
                dataset_duration_ms=None,
                message_id="disabled",
                error_code=disabled_result.error_code,
                error_description=disabled_result.error_description,
                raw_response=None,
            )

        try:
            dataset_result = dataset_fetcher()
        except DatasetValidationError as exc:
            return self._build_failure_result(
                dataset_id=dataset_id,
                message_id="dataset_validation_error",
                error_code=exc.error_code,
                error_description=str(exc),
            )
        except ReportPreparationError as exc:
            return self._build_failure_result(
                dataset_id=dataset_id,
                message_id="dataset_preparation_error",
                error_code="dataset_error",
                error_description=str(exc),
            )

        metadata = dataset_result.metadata
        message_id = metadata.message_id
        telegram_chat_id = self._client.chat_id if self._client.chat_id else None

        context = ensure_log_context(
            etapa="fase_6_telegram",
            message_id=message_id,
            dataset_id=dataset_id,
            branch_id=branch_id,
            telegram_chat_id=telegram_chat_id,
            records_processed=metadata.record_count,
            records_skipped=0,
        )
        logger = bind_log_context(self._logger, context)

        logger.info(
            "telegram_report_started",
            force_refresh=force_refresh,
            dataset_records=metadata.record_count,
        )

        if not metadata.record_count:
            text = self._format_empty_report(dataset_id=dataset_id, empty_message=empty_message, branch_id=branch_id)
            send_result = self._send_with_retries(text=text, message_id=message_id)
            log_event = "telegram_report_completed" if send_result.success else "telegram_report_error"
            logger.info(
                log_event,
                records_sent=send_result.records_sent,
                status_code=send_result.status_code,
                duration_ms=send_result.duration_ms,
                error_code=send_result.error_code,
            )
            return TelegramNotificationResult(
                success=send_result.success,
                telegram_message_id=send_result.telegram_message_id,
                records_sent=send_result.records_sent,
                status_code=send_result.status_code,
                duration_ms=send_result.duration_ms,
                dataset_id=dataset_id,
                dataset_records=metadata.record_count,
                dataset_duration_ms=metadata.duration_ms,
                message_id=message_id,
                error_code=send_result.error_code,
                error_description=send_result.error_description,
                raw_response=send_result.raw_response,
            )

        text = formatter(dataset_result)
        send_result = self._send_with_retries(text=text, message_id=message_id)
        log_event = "telegram_report_completed" if send_result.success else "telegram_report_error"
        logger.info(
            log_event,
            records_sent=send_result.records_sent,
            status_code=send_result.status_code,
            duration_ms=send_result.duration_ms,
            error_code=send_result.error_code,
        )

        return TelegramNotificationResult(
            success=send_result.success,
            telegram_message_id=send_result.telegram_message_id,
            records_sent=send_result.records_sent,
            status_code=send_result.status_code,
            duration_ms=send_result.duration_ms,
            dataset_id=dataset_id,
            dataset_records=metadata.record_count,
            dataset_duration_ms=metadata.duration_ms,
            message_id=message_id,
            error_code=send_result.error_code,
            error_description=send_result.error_description,
            raw_response=send_result.raw_response,
        )

    def _send_with_retries(self, *, text: str, message_id: str) -> TelegramSendResult:
        attempt = 0
        last_result: Optional[TelegramSendResult] = None

        while attempt < self._max_attempts:
            attempt += 1
            result = self._client.send_message(text=text, message_id=message_id)
            if result.success or not result.should_retry:
                return result
            last_result = result
            sleep_seconds = self._initial_backoff_seconds * (2 ** (attempt - 1))
            time.sleep(sleep_seconds)

        assert last_result is not None  # for mypy/static checkers
        return last_result

    def _format_empty_report(self, *, dataset_id: str, empty_message: str, branch_id: Optional[int]) -> str:
        header = self._build_header(dataset_id)
        footer = self._build_footer(branch_id)
        return f"{header}{empty_message}\n\n{footer}"

    @staticmethod
    def _build_header(dataset_id: str) -> str:
        if dataset_id == "upcoming_arrivals":
            return "📊 <b>Próximos Ingresos al CCM</b>\n\n"
        if dataset_id == "upcoming_birthdays":
            return "🎊 <b>PRÓXIMOS CUMPLEAÑOS</b>\n"
        return "ℹ️ <b>CCM Notifications</b>\n\n"

    def _build_footer(self, branch_id: Optional[int]) -> str:
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        rama = branch_id or self._report_service.default_branch_id or "N/A"
        return f"🕐 {timestamp}\n🏢 Rama {rama} - CCM Sistema"

    def _format_upcoming_arrivals(self, dataset_result: ReportDatasetResult) -> str:
        records = dataset_result.data
        grouped = self._group_arrivals(records)
        header = self._build_header("upcoming_arrivals")
        lines: List[str] = [header]
        today = date.today()

        for arrival_date, entries in grouped:
            diff_days = (arrival_date - today).days
            descriptor = self._arrival_time_descriptor(diff_days)
            formatted_date = arrival_date.strftime("%d/%m/%Y")
            total = sum(entry["missionaries_count"] for entry in entries)
            lines.append(f"◆ <b>{descriptor}</b> ({formatted_date})")
            lines.append(f"◆ Total: {total} misioneros\n")

            for entry in entries:
                district = entry["district"]
                rdistrict = entry.get("rdistrict") or "-"
                lines.append(f"📍 <b>Distrito {district}</b> ({rdistrict})")
                lines.append(self._format_people_count(entry["missionaries_count"]))
                duration = entry.get("duration_weeks")
                if duration:
                    lines.append(f"⏱️ Duración: {duration} semanas")
                arrival = arrival_date.strftime("%d/%m/%Y")
                lines.append(f"◆ Entrada: {arrival}")
                departure = entry.get("departure_date")
                if departure:
                    if isinstance(departure, str):
                        departure_date = date.fromisoformat(departure)
                    else:
                        departure_date = departure
                    lines.append(f"◆ Salida: {departure_date.strftime('%d/%m/%Y')}")
                else:
                    lines.append("◆ Salida: Por definir")
                lines.append("")

        footer = self._build_footer(dataset_result.metadata.branch_id)
        lines.append(footer)
        return "\n".join(lines).strip()

    def _format_upcoming_birthdays(self, dataset_result: ReportDatasetResult) -> str:
        records = dataset_result.data
        grouped = self._group_birthdays(records)
        header = self._build_header("upcoming_birthdays")
        lines: List[str] = [header]
        lines.append(f"📅 {datetime.now().strftime('%d/%m/%Y')}")
        rama = dataset_result.metadata.branch_id or self._report_service.default_branch_id or "N/A"
        lines.append(f"🎯 Ramas: {rama}\n")

        if not grouped:
            footer = self._build_footer(dataset_result.metadata.branch_id)
            lines.append(footer)
            return "\n".join(lines).strip()

        for month_name, days in grouped:
            lines.append(f"🗓️ <b>{month_name}</b>:")
            for day, birthdays in days:
                for entry in birthdays:
                    treatment = entry.get("treatment") or entry.get("missionary_name")
                    age = entry.get("age_turning")
                    status = entry.get("status") or "CCM"
                    lines.append(
                        f"📅 {day:02d} - {treatment} ({age}-{status})"
                    )
            lines.append("")

        footer = self._build_footer(dataset_result.metadata.branch_id)
        lines.append(footer)
        return "\n".join(lines).strip()

    def _format_alert(self, *, title: str, body: str, level: str, branch_id: Optional[int]) -> str:
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅",
        }.get(level.lower(), "ℹ️")
        header = f"{emoji} <b>{title}</b>\n\n"
        footer = self._build_footer(branch_id)
        return f"{header}{body}\n\n{footer}"

    @staticmethod
    def _arrival_time_descriptor(diff_days: int) -> str:
        if diff_days <= 7:
            return "La próxima semana"
        if diff_days <= 14:
            return "En 2 semanas"
        if diff_days <= 21:
            return "En 3 semanas"
        if diff_days <= 30:
            return "Este mes"
        return f"En {diff_days} días"

    @staticmethod
    def _format_people_count(count: int) -> str:
        suffix = "s" if count != 1 else ""
        return f"👥 {count} misionero{suffix}"

    def _group_arrivals(self, records: Iterable[Dict[str, object]]) -> List[Tuple[date, List[Dict[str, object]]]]:
        groups: Dict[date, List[Dict[str, object]]] = {}
        for record in records:
            arrival = record.get("arrival_date")
            if isinstance(arrival, str):
                arrival_date = date.fromisoformat(arrival)
            else:
                arrival_date = arrival  # type: ignore[assignment]
            if arrival_date is None:
                continue
            key = arrival_date
            groups.setdefault(key, []).append(record)
        return sorted((key, groups[key]) for key in groups)

    def _group_birthdays(
        self, records: Iterable[Dict[str, object]]
    ) -> List[Tuple[str, List[Tuple[int, List[Dict[str, object]]]]]]:
        month_names = {
            1: "ENERO",
            2: "FEBRERO",
            3: "MARZO",
            4: "ABRIL",
            5: "MAYO",
            6: "JUNIO",
            7: "JULIO",
            8: "AGOSTO",
            9: "SEPTIEMBRE",
            10: "OCTUBRE",
            11: "NOVIEMBRE",
            12: "DICIEMBRE",
        }
        months: Dict[int, Dict[int, List[Dict[str, object]]]] = {}
        for record in records:
            birthday = record.get("birthday")
            if isinstance(birthday, str):
                birthday_date = date.fromisoformat(birthday)
            else:
                birthday_date = birthday  # type: ignore[assignment]
            if birthday_date is None:
                continue
            month = birthday_date.month
            day = birthday_date.day
            months.setdefault(month, {}).setdefault(day, []).append(record)

        result: List[Tuple[str, List[Tuple[int, List[Dict[str, object]]]]]] = []
        for month in sorted(months):
            days = months[month]
            day_entries = sorted((day, days[day]) for day in days)
            result.append((month_names.get(month, str(month)), day_entries))
        return result

    @staticmethod
    def _build_failure_result(
        *,
        dataset_id: str,
        message_id: str,
        error_code: str,
        error_description: str,
    ) -> TelegramNotificationResult:
        return TelegramNotificationResult(
            success=False,
            telegram_message_id=None,
            records_sent=0,
            status_code=0,
            duration_ms=0,
            dataset_id=dataset_id,
            dataset_records=0,
            dataset_duration_ms=None,
            message_id=message_id,
            error_code=error_code,
            error_description=error_description,
            raw_response=None,
        )
