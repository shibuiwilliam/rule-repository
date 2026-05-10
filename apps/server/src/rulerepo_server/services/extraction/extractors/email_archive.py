"""Email archive extractor — discovers de-facto patterns from past email corpora.

Output is INFO-modality candidates by default — these become "templates",
not "musts". See CLAUDE.md §14.11.
"""

from __future__ import annotations

import email
import re
from pathlib import Path
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)


class EmailArchiveExtractor:
    """Discovers communication patterns from email archives.

    Finds recurring phrasings, signature conventions, disclaimers,
    and other patterns that may indicate de-facto rules.
    """

    source_types = ["email_archive"]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from an email archive directory.

        Args:
            source: The email archive source (directory path or single .eml).

        Returns:
            List of CandidateRule, mostly INFO modality.
        """
        logger.info("email_archive_extraction_started", path=str(source.path))

        emails = self._load_emails(source.path)
        patterns = self._find_patterns(emails)

        candidates: list[CandidateRule] = []
        for pattern in patterns:
            candidates.append(
                CandidateRule(
                    statement=pattern["statement"],
                    modality="INFO",
                    severity="LOW",
                    source_refs={
                        "document": str(source.path),
                        "type": "email_pattern",
                        "occurrences": pattern["count"],
                    },
                    department=source.metadata.get("department", "public"),
                    tags=["email", "pattern", "de-facto"],
                    applicable_subject_kinds=["creative", "document"],
                    confidence=min(pattern["count"] / 10.0, 0.8),
                )
            )

        logger.info("email_archive_extraction_complete", candidates=len(candidates))
        return candidates

    def _load_emails(self, path: Path) -> list[dict[str, str]]:
        """Load emails from a directory of .eml files or a single file."""
        emails: list[dict[str, str]] = []

        if path.is_file() and path.suffix == ".eml":
            parsed = self._parse_eml(path)
            if parsed:
                emails.append(parsed)
        elif path.is_dir():
            for eml_path in sorted(path.glob("**/*.eml"))[:100]:
                parsed = self._parse_eml(eml_path)
                if parsed:
                    emails.append(parsed)

        return emails

    def _parse_eml(self, path: Path) -> dict[str, str] | None:
        """Parse a single .eml file."""
        try:
            with open(path, "rb") as f:
                msg = email.message_from_binary_file(f)

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(charset, errors="replace")
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors="replace")

            return {
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "body": body,
            }
        except Exception as exc:
            logger.warning("eml_parse_failed", path=str(path), error=str(exc))
            return None

    def _find_patterns(self, emails: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Find recurring patterns across emails."""
        patterns: list[dict[str, Any]] = []

        # Find common disclaimers
        disclaimer_counts: dict[str, int] = {}
        disclaimer_re = re.compile(
            r"(?:disclaimer|confidential|notice|免責|機密|注意).*?(?:\n\n|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        for em in emails:
            for match in disclaimer_re.finditer(em.get("body", "")):
                text = match.group(0).strip()[:200]
                if len(text) > 20:
                    disclaimer_counts[text] = disclaimer_counts.get(text, 0) + 1

        for text, count in disclaimer_counts.items():
            if count >= 2:
                patterns.append(
                    {
                        "statement": f"Email communications should include: {text}",
                        "count": count,
                    }
                )

        # Find common signature patterns
        sig_counts: dict[str, int] = {}
        for em in emails:
            body = em.get("body", "")
            sig_marker = body.rfind("--\n")
            if sig_marker > 0:
                sig = body[sig_marker + 3 :].strip()[:100]
                if sig:
                    sig_counts[sig] = sig_counts.get(sig, 0) + 1

        for sig, count in sig_counts.items():
            if count >= 3:
                patterns.append(
                    {
                        "statement": f"Standard email signature format observed: {sig}",
                        "count": count,
                    }
                )

        return patterns
