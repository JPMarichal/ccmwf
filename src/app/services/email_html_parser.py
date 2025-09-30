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

    # Prefer <thead>, otherwise first row as header
    thead = table.find("thead")
    if thead:
        header_cells = thead.find_all(["th", "td"])
    else:
        first_row = table.find("tr")
        header_cells = first_row.find_all(["th", "td"]) if first_row else []
        # remove first_row from table rows to avoid duplication later
        if first_row:
            first_row.extract()

    for cell in header_cells:
        text = cell.get_text(strip=True)
        if text:
            headers.append(text)

    if not headers:
        errors.append("headers_missing")
        return None, errors

    tbody = table.find("tbody")
    if tbody:
        row_candidates = tbody.find_all("tr")
    else:
        row_candidates = table.find_all("tr")

    for row in row_candidates:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_values = [cell.get_text(strip=True) for cell in cells]
        # only keep rows with some non-empty content
        if any(value for value in row_values):
            rows.append(row_values)

    if not rows:
        errors.append("rows_missing")
        return None, errors

    # Normalize rows to dicts using headers
    normalized_rows: List[Dict[str, str]] = []
    header_count = len(headers)
    for row in rows:
        padded = row + [""] * (header_count - len(row))
        normalized_rows.append({headers[i]: padded[i] for i in range(header_count)})

    return {"headers": headers, "rows": normalized_rows}, errors
