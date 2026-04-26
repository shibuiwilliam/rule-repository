"""PII sanitization — detect and mask personally identifiable information.

PROJECT.md §7.3: "PII sanitization on inputs and masking on logs."

Applied before sending content to Gemini and when storing details in audit logs.
Uses pattern-based detection for common PII types. This is a best-effort filter;
it does not replace proper data governance controls.
"""

from __future__ import annotations

import re

# Pattern name → (compiled regex, replacement mask)
_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[EMAIL_REDACTED]",
    ),
    (
        "phone_us",
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "[PHONE_REDACTED]",
    ),
    (
        "phone_jp",
        re.compile(r"\b0\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{3,4}\b"),
        "[PHONE_REDACTED]",
    ),
    (
        "ssn_us",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[SSN_REDACTED]",
    ),
    (
        "credit_card",
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        "[CARD_REDACTED]",
    ),
    (
        "my_number_jp",
        re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
        "[MYNUMBER_REDACTED]",
    ),
    (
        "ip_address",
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "[IP_REDACTED]",
    ),
]


def sanitize_text(text: str) -> str:
    """Replace PII patterns in text with redaction markers.

    Args:
        text: The input text that may contain PII.

    Returns:
        Text with PII patterns replaced by [TYPE_REDACTED] markers.
    """
    result = text
    for _name, pattern, mask in _PII_PATTERNS:
        result = pattern.sub(mask, result)
    return result


def sanitize_dict(data: dict[str, object], *, deep: bool = True) -> dict[str, object]:
    """Sanitize string values in a dictionary.

    Args:
        data: Dictionary that may contain PII in string values.
        deep: If True, recurse into nested dicts and lists.

    Returns:
        A new dictionary with PII replaced in string values.
    """
    result: dict[str, object] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_text(value)
        elif deep and isinstance(value, dict):
            result[key] = sanitize_dict(value, deep=True)  # type: ignore[arg-type]
        elif deep and isinstance(value, list):
            result[key] = [sanitize_text(item) if isinstance(item, str) else item for item in value]
        else:
            result[key] = value
    return result


def contains_pii(text: str) -> bool:
    """Check whether text contains any detectable PII patterns.

    Args:
        text: The text to check.

    Returns:
        True if any PII pattern matches.
    """
    return any(pattern.search(text) for _name, pattern, _mask in _PII_PATTERNS)
