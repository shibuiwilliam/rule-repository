"""Extractor for CLAUDE.md files — extracts rule candidates from
imperative statements in Claude Code instruction files.

CLAUDE.md files contain natural-language directives for AI assistants.
Many of these directives are implicit rules that can be formalized.

See: CLAUDE.md SS16
"""

from __future__ import annotations

import re
from typing import Any

# Patterns that indicate an imperative/normative statement
_IMPERATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"^\s*[-*]\s*(must|shall|should|always|never|do not|don't|avoid|ensure|require|prefer)\b", re.IGNORECASE
    ),
    re.compile(
        r"^\s*[-*]\s*\*\*(must|shall|should|always|never|do not|don't|avoid|ensure|require|prefer)\b", re.IGNORECASE
    ),
    re.compile(
        r"^\s*\d+\.\s*(must|shall|should|always|never|do not|don't|avoid|ensure|require|prefer)\b", re.IGNORECASE
    ),
    re.compile(r"^(must|shall|should|always|never|do not|don't|avoid|ensure|require|prefer)\b", re.IGNORECASE),
]

# Modality detection from statement keywords
_MODALITY_MAP: dict[str, str] = {
    "must": "MUST",
    "shall": "MUST",
    "always": "MUST",
    "never": "MUST_NOT",
    "do not": "MUST_NOT",
    "don't": "MUST_NOT",
    "avoid": "SHOULD",
    "should": "SHOULD",
    "prefer": "MAY",
    "ensure": "MUST",
    "require": "MUST",
}


def _detect_modality(statement: str) -> str:
    """Detect the modality of a statement from its keywords.

    Args:
        statement: The rule statement text.

    Returns:
        Modality string (MUST, MUST_NOT, SHOULD, MAY).
    """
    lower = statement.lower()
    for keyword, modality in _MODALITY_MAP.items():
        if keyword in lower:
            return modality
    return "SHOULD"


def _extract_section(text: str) -> list[tuple[str, str]]:
    """Split text into (heading, content) sections.

    Args:
        text: Full CLAUDE.md content.

    Returns:
        List of (heading, content) tuples.
    """
    sections: list[tuple[str, str]] = []
    current_heading = "General"
    current_lines: list[str] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading_match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = heading_match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections


def _is_imperative(line: str) -> bool:
    """Check if a line contains an imperative/normative statement.

    Args:
        line: A single line of text.

    Returns:
        True if the line matches an imperative pattern.
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 10:
        return False
    return any(pattern.match(stripped) for pattern in _IMPERATIVE_PATTERNS)


def _clean_statement(line: str) -> str:
    """Clean a statement by removing list markers and formatting.

    Args:
        line: Raw line text.

    Returns:
        Cleaned statement text.
    """
    cleaned = line.strip()
    # Remove list markers
    cleaned = re.sub(r"^\s*[-*]\s*", "", cleaned)
    cleaned = re.sub(r"^\s*\d+\.\s*", "", cleaned)
    # Remove bold markers
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    # Remove inline code markers
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    return cleaned.strip()


def _derive_scope(heading: str, metadata: dict[str, Any]) -> list[str]:
    """Derive rule scopes from section heading and metadata.

    Args:
        heading: The section heading containing this statement.
        metadata: Extraction metadata (filename, project, ...).

    Returns:
        List of scope strings.
    """
    scopes: list[str] = []
    lower_heading = heading.lower()

    if any(kw in lower_heading for kw in ("python", "backend", "server")):
        scopes.append("engineering/python")
    if any(kw in lower_heading for kw in ("typescript", "frontend", "react", "next")):
        scopes.append("engineering/typescript")
    if any(kw in lower_heading for kw in ("test", "testing")):
        scopes.append("engineering/testing")
    if any(kw in lower_heading for kw in ("convention", "style", "naming", "format")):
        scopes.append("engineering/conventions")
    if any(kw in lower_heading for kw in ("security", "auth")):
        scopes.append("engineering/security")
    if any(kw in lower_heading for kw in ("deploy", "ci", "docker", "infra")):
        scopes.append("engineering/devops")
    if any(kw in lower_heading for kw in ("api", "endpoint", "route")):
        scopes.append("engineering/api")
    if any(kw in lower_heading for kw in ("database", "migration", "sql")):
        scopes.append("engineering/database")

    if not scopes:
        scopes.append("engineering")

    return scopes


class ClaudeMdExtractor:
    """Extracts rule candidates from CLAUDE.md files.

    Parses the document structure, identifies imperative statements,
    and produces candidate rules with modality, scope, and rationale
    derived from the document context.
    """

    @property
    def name(self) -> str:
        return "claude_md"

    @property
    def domain(self) -> str:
        return "engineering"

    @property
    def supported_source_types(self) -> list[str]:
        return ["claude_md", "markdown"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract rule candidates from CLAUDE.md content.

        Args:
            content: Raw bytes of the CLAUDE.md file.
            source_type: Must be 'claude_md' or 'markdown'.
            metadata: Additional metadata (filename, project, author, ...).

        Returns:
            List of candidate rule dicts, each containing:
            statement, modality, severity, scope, rationale, source.
        """
        text = content.decode("utf-8", errors="replace")
        sections = _extract_section(text)
        candidates: list[dict[str, Any]] = []

        for heading, section_content in sections:
            for line in section_content.split("\n"):
                if not _is_imperative(line):
                    continue

                statement = _clean_statement(line)
                if len(statement) < 15:
                    continue

                modality = _detect_modality(statement)
                scopes = _derive_scope(heading, metadata)

                candidates.append(
                    {
                        "statement": statement,
                        "modality": modality,
                        "severity": "MEDIUM",
                        "scope": scopes,
                        "rationale": (
                            f"Extracted from CLAUDE.md section '{heading}'. "
                            f"This directive was identified as an imperative "
                            f"statement suitable for formalization as a rule."
                        ),
                        "source": {
                            "type": source_type,
                            "filename": metadata.get("filename", "CLAUDE.md"),
                            "section": heading,
                            "original_text": line.strip(),
                        },
                        "tags": ["auto-extracted", "claude-md"],
                        "applicable_subject_types": ["code_diff"],
                    }
                )

        return candidates
