"""Helpers for extracting structured data from missionary arrival emails."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_MONTH_ALIASES = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "sept": "09",
    "octubre": "10",
    "oct": "10",
    "noviembre": "11",
    "diciembre": "12",
}

_PATTERN_GENERACION = re.compile(
    r"Generación\s+del\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)
_PATTERN_GENERIC = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(?:de\s+)?(\d{4})",
    re.IGNORECASE,
)


def _normalize_month_name(value: str) -> Optional[str]:
    """Normalize Spanish month names (with optional accents) to numbers."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    return _MONTH_ALIASES.get(normalized)


def _parse_with_patterns(
    content: str,
    patterns: Sequence[re.Pattern[str]],
) -> Optional[Tuple[str, str]]:
    """Try each pattern and return the formatted date with the original match."""

    for pattern in patterns:
        match = pattern.search(content)
        if not match:
            continue

        day = match.group(1).zfill(2)
        month_name = match.group(2)
        year = match.group(3)

        month = _normalize_month_name(month_name)
        if not month:
            continue

        formatted = f"{year}{month}{day}"
        return formatted, match.group(0)

    return None


def extract_fecha_generacion(
    logger: Optional[Any],
    body: str,
    html: Optional[str] = None,
    subject: Optional[str] = None,
    table_texts: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """Extract the generación date from multiple text sources.

    Parameters
    ----------
    logger:
        Logger used to record structured events.
    body:
        Plain text body extracted from the email message.
    html:
        Raw HTML body. Used as fallback when the plain text body is empty.
    subject:
        Email subject.
    table_texts:
        Additional textual hints coming from parsed table headers/rows.
    """

    sources: List[Tuple[str, str, Sequence[re.Pattern[str]]]] = []

    if body:
        sources.append(("cuerpo_texto", body, (_PATTERN_GENERACION, _PATTERN_GENERIC)))
    if html:
        sources.append(("cuerpo_html", html, (_PATTERN_GENERACION, _PATTERN_GENERIC)))
    if table_texts:
        for text in table_texts:
            if text:
                sources.append(("tabla_html", text, (_PATTERN_GENERACION, _PATTERN_GENERIC)))
    if subject:
        sources.append(("asunto", subject, (_PATTERN_GENERIC,)))

    for source_name, content, patterns in sources:
        parsed = _parse_with_patterns(content, patterns)
        if parsed:
            formatted, original_text = parsed
            if logger:
                logger.info(
                    "📅 Fecha de generación extraída",
                    fuente=source_name,
                    fecha_original=original_text,
                    fecha_formateada=formatted,
                )
            return formatted

    if logger:
        logger.warning(
            "⚠️ No se pudo extraer fecha de generación",
            fuente="parseo_fechas",
            body_preview=(body or "")[:100],
            subject=subject or "",
            fuentes_consultadas=[source for source, _, _ in sources],
        )

    return None


def collect_table_texts(parsed_table: Optional[Dict[str, Any]]) -> List[str]:
    """Collect textual content from table headers and rows for auxiliary parsing."""

    if not parsed_table:
        return []

    texts: List[str] = []

    headers = parsed_table.get("headers") or []
    texts.extend(str(header) for header in headers if header)

    for row in parsed_table.get("rows") or []:
        if isinstance(row, dict):
            texts.extend(str(value) for value in row.values() if value)

    extra = parsed_table.get("extra_texts") or []
    texts.extend(str(value) for value in extra if value)

    return texts
