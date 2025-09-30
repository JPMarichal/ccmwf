"""Utility helpers for validating incoming email messages."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional

from app.models import EmailAttachment


_SUBJECT_NORMALIZER = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return _SUBJECT_NORMALIZER.sub(" ", value.strip()).lower()


def validate_email_structure(
    subject: str,
    fecha_generacion: Optional[str],
    attachments: Iterable[EmailAttachment],
    expected_subject_pattern: str,
) -> tuple[bool, List[str]]:
    """Validate mandatory pieces of an email and return (is_valid, errors).

    Parameters
    ----------
    subject:
        Subject extracted from the incoming email.
    fecha_generacion:
        Date string in YYYYMMDD format parsed from the body.
    attachments:
        Iterable of `EmailAttachment` already extracted from the message.
    expected_subject_pattern:
        Pattern that should appear within the subject (case-insensitive).
    """

    errors: List[str] = []

    normalized_subject = _normalize(subject) if subject else ""
    normalized_pattern = _normalize(expected_subject_pattern)
    if not normalized_subject or normalized_pattern not in normalized_subject:
        errors.append("subject_pattern_mismatch")

    if not fecha_generacion:
        errors.append("fecha_generacion_missing")

    attachments_list = list(attachments)
    if not attachments_list:
        errors.append("attachments_missing")
    else:
        has_pdf = any(
            (attachment.content_type or "").lower() == "application/pdf"
            or (attachment.filename or "").lower().endswith(".pdf")
            for attachment in attachments_list
        )
        if not has_pdf:
            errors.append("pdf_attachment_missing")

    return (len(errors) == 0, errors)
