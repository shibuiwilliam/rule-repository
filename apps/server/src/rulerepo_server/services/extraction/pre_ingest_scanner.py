"""Pre-ingest scanner -- checks documents for secrets and PII before ingestion (RR-031).

Scans content before it enters the rule extraction pipeline to prevent
secrets and PII from being stored or sent to LLM providers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScanResult:
    """Result of a pre-ingest content scan.

    Attributes:
        safe: True if no secrets were detected. Note that PII detection
            is advisory and does not set ``safe`` to False by itself.
        findings: List of finding dicts with ``type``, ``pattern``/``field``,
            and ``location`` keys.
        pii_detected: True if potential PII fields were found.
        secrets_detected: True if secret patterns were matched.
    """

    safe: bool = True
    findings: list[dict[str, str]] = field(default_factory=list)
    pii_detected: bool = False
    secrets_detected: bool = False


# Patterns for common secrets
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    ),
    ("github_token", re.compile(r"gh[ps]_[A-Za-z0-9_]{36,}")),
    (
        "api_key_generic",
        re.compile(
            r"(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9]{20,}",
        ),
    ),
    (
        "bearer_token",
        re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}"),
    ),
    (
        "password_assignment",
        re.compile(
            r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}",
        ),
    ),
    (
        "connection_string",
        re.compile(r"(?:mongodb|postgres|mysql|redis)://[^\s]{10,}"),
    ),
    (
        "slack_webhook",
        re.compile(
            r"https://hooks\.slack\.com/services/"
            r"T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
        ),
    ),
]


def scan_content(content: str) -> ScanResult:
    """Scan content for secrets and PII before ingestion.

    Checks for common secret patterns (AWS keys, private keys, tokens,
    passwords, connection strings) and delegates PII detection to the
    existing ``core.pii.redactor.detect_pii`` function.

    Args:
        content: The raw text content to scan.

    Returns:
        A :class:`ScanResult` describing any findings.
    """
    result = ScanResult()

    # Secret detection
    for name, pattern in _SECRET_PATTERNS:
        if match := pattern.search(content):
            result.safe = False
            result.secrets_detected = True
            result.findings.append(
                {
                    "type": "secret",
                    "pattern": name,
                    "location": f"offset {match.start()}",
                }
            )

    # PII detection via existing redactor
    from rulerepo_server.core.pii.redactor import detect_pii

    pii_paths = detect_pii({"content": content})
    if pii_paths:
        result.pii_detected = True
        for path in pii_paths:
            result.findings.append({"type": "pii", "field": path})

    if not result.safe or result.pii_detected:
        logger.warning(
            "pre_ingest_scan_findings",
            secrets=result.secrets_detected,
            pii=result.pii_detected,
            finding_count=len(result.findings),
        )

    return result
