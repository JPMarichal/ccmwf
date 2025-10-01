"""Utilities for parsing and validating HTML tables embedded in CCM arrival emails."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


ParsedTable = Dict[str, Any]


def extract_primary_table(html: str) -> Tuple[Optional[ParsedTable], List[str]]:
    """Extract the first meaningful table from the HTML body.

    Returns a tuple with the parsed table (headers + rows) and a list of error codes.
    """

    errors: List[str] = []
    if not html or not html.strip():
        errors.append("html_missing")
        return None, errors

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        errors.append("table_missing")
        return None, errors

    headers: List[str] = []
    rows: List[List[str]] = []
    extra_texts: List[str] = []

    all_rows = table.find_all("tr")

    header_row_found = False
    for row in all_rows:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue

        cell_texts = [cell.get_text(strip=True) for cell in cells]
        non_empty = [text for text in cell_texts if text]

        # Identify header row: prefer rows with explicit <th>, otherwise first
        # row with more than one meaningful cell.
        if not header_row_found:
            has_th = any(cell.name.lower() == "th" for cell in cells)
            if has_th or len(non_empty) > 1:
                candidate_headers = [text for text in cell_texts if text]
                if candidate_headers:
                    headers = candidate_headers
                    header_row_found = True
                    continue
            if non_empty:
                extra_texts.extend(non_empty)
            continue

        # Remaining rows are considered data rows.
        if header_row_found and any(text for text in cell_texts):
            rows.append(cell_texts)

    if not headers:
        errors.append("headers_missing")
        return None, errors

    if not rows:
        errors.append("rows_missing")

    # Normalize rows to dicts using headers
    normalized_rows: List[Dict[str, str]] = []
    header_count = len(headers)
    for row in rows:
        padded = row + [""] * (header_count - len(row))
        normalized_rows.append({headers[i]: padded[i] for i in range(header_count)})

    return {"headers": headers, "rows": normalized_rows, "extra_texts": extra_texts}, errors
