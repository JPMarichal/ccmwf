"""Utilities for parsing and validating HTML tables embedded in CCM arrival emails."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup


ParsedTable = Dict[str, Any]


def extract_primary_table(html: str) -> Tuple[Optional[ParsedTable], List[str]]:
    """Extract the most relevant CCM data table from the HTML body.

    The parser iterates over every table found in the email, computes a heuristic
    score based on expected headers and content, and returns the best match. When
    no suitable table is detected, an explicit error code is emitted so the caller
    can react accordingly.
    """

    errors: List[str] = []
    if not html or not html.strip():
        errors.append("html_missing")
        return None, errors

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        errors.append("table_missing")
        return None, errors

    best_candidate: Optional[Tuple[ParsedTable, List[str], float, int]] = None
    fallback_errors: List[str] = []

    for index, table in enumerate(tables):
        parsed_table, candidate_errors = _parse_table_element(table)
        if not parsed_table:
            fallback_errors.extend(candidate_errors)
            continue

        score = _score_table(parsed_table)
        if best_candidate is None or score > best_candidate[2]:
            best_candidate = (parsed_table, candidate_errors, score, index)

    if best_candidate:
        parsed_table, candidate_errors, _, _ = best_candidate
        return parsed_table, candidate_errors

    # No table produced a valid header row. Surface the most informative error.
    errors.extend(sorted(set(fallback_errors)) or ["table_candidate_missing"])
    return None, errors


def _parse_table_element(table) -> Tuple[Optional[ParsedTable], List[str]]:
    headers: List[str] = []
    rows: List[List[str]] = []
    extra_texts: List[str] = []
    errors: List[str] = []

    all_rows = table.find_all("tr")
    header_row_found = False

    for row in all_rows:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue

        cell_texts = [cell.get_text(strip=True) for cell in cells]
        non_empty = [text for text in cell_texts if text]

        if not header_row_found:
            has_th = any(cell.name and cell.name.lower() == "th" for cell in cells)
            if has_th or len(non_empty) > 1:
                candidate_headers = [text for text in cell_texts if text]
                if candidate_headers:
                    headers = candidate_headers
                    header_row_found = True
                    continue
            if non_empty:
                extra_texts.extend(non_empty)
            continue

        if header_row_found:
            non_empty_count = sum(bool(text.strip()) for text in cell_texts)
            if non_empty_count == 0:
                continue
            if non_empty_count <= 1:
                # Filtrar filas de separadores como "6 SEMANAS"
                continue
            rows.append(cell_texts)

    if not headers:
        errors.append("headers_missing")
        return None, errors

    normalized_rows: List[Dict[str, str]] = []
    header_count = len(headers)
    for row in rows:
        if not any(text.strip() for text in row):
            continue
        padded = row + [""] * (header_count - len(row))
        row_dict = {headers[i]: padded[i] for i in range(header_count)}
        if _row_resembles_headers(row_dict, headers):
            continue
        normalized_rows.append(row_dict)

    if not normalized_rows:
        errors.append("rows_missing")

    return {"headers": headers, "rows": normalized_rows, "extra_texts": extra_texts}, errors


def _score_table(parsed_table: ParsedTable) -> float:
    """Assign a heuristic score to a parsed table to detect CCM payloads."""

    headers = parsed_table.get("headers", [])
    rows: Iterable[Dict[str, str]] = parsed_table.get("rows", [])

    normalized_headers = [_normalize_text(header) for header in headers if isinstance(header, str)]
    if not normalized_headers:
        return 0.0

    keyword_matches = sum(1 for header in normalized_headers if _header_matches_expected(header))
    row_count = len(list(rows))

    # Re-evaluate rows as list since we consumed it for len.
    rows = parsed_table.get("rows", [])

    numeric_ratio = _numeric_signal(rows, headers)

    score = keyword_matches * 10 + min(row_count, 50)
    if numeric_ratio >= 0.6:
        score += 5
    if any("generacion" in header for header in normalized_headers):
        score += 3
    if keyword_matches < 2:
        score -= 5

    return score


def _header_matches_expected(header: str) -> bool:
    expected_fragments = {
        "distrito",
        "zona",
        "zona horaria",
        "observaciones",
        "rama",
        "hermanas",
        "elder",
        "total",
        "generacion",
    }
    return any(fragment in header for fragment in expected_fragments)


def _numeric_signal(rows: Iterable[Dict[str, str]], headers: List[str]) -> float:
    if not rows:
        return 0.0

    numeric_headers = []
    for header in headers:
        normalized = _normalize_text(header)
        if any(fragment in normalized for fragment in {"rama", "total", "hermanas", "elder"}):
            numeric_headers.append(header)

    if not numeric_headers:
        return 0.0

    total_cells = len(numeric_headers) * len(rows)
    if total_cells == 0:
        return 0.0

    numeric_cells = 0
    for row in rows:
        for header in numeric_headers:
            value = row.get(header, "")
            if _looks_numeric(value):
                numeric_cells += 1

    return numeric_cells / total_cells


def _looks_numeric(value: str) -> bool:
    if value is None:
        return False
    stripped = value.replace(",", "").replace(" ", "")
    return bool(stripped) and stripped.replace(".", "", 1).isdigit()


def _normalize_text(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.strip().lower()


def _row_resembles_headers(row: Dict[str, str], headers: List[str]) -> bool:
    """Detect rows that duplicate header labels to evitar falsos positivos."""

    normalized_headers = {_normalize_text(header) for header in headers}
    normalized_values = {_normalize_text(value) for value in row.values() if value}
    return normalized_values and normalized_values <= normalized_headers
