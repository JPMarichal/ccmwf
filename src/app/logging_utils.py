"""Utilidades para estandarizar el contexto de logging estructurado."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import structlog

# Campos obligatorios según lineamientos de logging
MANDATORY_FIELDS: Iterable[str] = (
    "message_id",
    "etapa",
    "drive_folder_id",
    "excel_file_id",
    "request_id",
    "batch_size",
    "records_processed",
    "records_skipped",
    "error_code",
)


def ensure_log_context(
    base: Optional[Dict[str, Any]] = None,
    *,
    etapa: Optional[str] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """Genera un contexto de logging con campos obligatorios.

    Args:
        base: Contexto previo a clonar/actualizar.
        etapa: Etapa del proceso actual.
        **overrides: Campos adicionales o reemplazos.

    Returns:
        Diccionario con todos los campos obligatorios presentes (usando ``None`` cuando no se
        proporcionan valores) y los overrides aplicados.
    """

    context: Dict[str, Any] = {field: None for field in MANDATORY_FIELDS}

    if base:
        context.update(base)

    if etapa is not None:
        context["etapa"] = etapa

    for key, value in overrides.items():
        context[key] = value

    return context


def bind_log_context(
    logger: structlog.stdlib.BoundLogger,
    context: Optional[Dict[str, Any]],
    **extra: Any,
) -> structlog.stdlib.BoundLogger:
    """Devuelve un logger con el contexto obligatorio unido.

    Args:
        logger: Instancia base de ``structlog``.
        context: Contexto preconstruido.
        **extra: Campos adicionales a unir al logger.

    Returns:
        ``BoundLogger`` con los campos filtrados (excluye claves con valor ``None``).
    """

    merged: Dict[str, Any] = {}

    if context:
        merged.update(context)

    for key, value in extra.items():
        merged[key] = value

    filtered = {key: value for key, value in merged.items() if value is not None}

    if not filtered:
        return logger

    return logger.bind(**filtered)
