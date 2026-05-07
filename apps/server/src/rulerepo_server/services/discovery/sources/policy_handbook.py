"""Policy handbook ingestion — extracts rules from internal policy documents.

Handles markdown, plain text, and structured policy formats. Uses
keyword-based extraction for normative sentences (MUST, SHALL, SHOULD,
MUST NOT, etc.) and structural parsing for numbered/bulleted sections.

Phase 7c.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Patterns for normative sentences
_NORMATIVE_PATTERNS = [
    re.compile(r"(?:employees?|staff|personnel|workers?)\s+(?:must|shall|should|may)\b", re.IGNORECASE),
    re.compile(r"\bmust\s+(?:not\s+)?(?:be|have|include|provide|ensure|submit|obtain|report)\b", re.IGNORECASE),
    re.compile(r"\bshall\s+(?:not\s+)?\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are)\s+(?:required|prohibited|not\s+permitted|mandatory)\b", re.IGNORECASE),
    re.compile(r"(?:しなければならない|してはならない|するものとする|努めなければならない|なければならない)"),
]

# Section heading patterns
_HEADING_PATTERN = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)
_NUMBERED_HEADING = re.compile(r"^(?:Article|Section|Rule|Chapter|\d+\.)\s+(.+)$", re.MULTILINE | re.IGNORECASE)


@dataclass
class PolicyCandidate:
    """A candidate rule extracted from a policy handbook."""

    statement: str
    section: str = ""
    modality: str = "SHOULD"
    severity: str = "MEDIUM"
    scope: list[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.0


def _detect_modality(text: str) -> str:
    """Detect modality from text content."""
    lower = text.lower()
    if any(kw in lower for kw in ["must not", "shall not", "prohibited", "not permitted", "してはならない"]):
        return "MUST_NOT"
    if any(kw in lower for kw in ["must", "shall", "required", "mandatory", "しなければならない"]):
        return "MUST"
    if any(kw in lower for kw in ["should", "recommended", "望ましい", "努め"]):
        return "SHOULD"
    if any(kw in lower for kw in ["may", "optional", "できる"]):
        return "MAY"
    return "SHOULD"


def _detect_severity(text: str) -> str:
    """Estimate severity from text content."""
    lower = text.lower()
    if any(kw in lower for kw in ["criminal", "termination", "immediate", "violation of law", "禁止"]):
        return "CRITICAL"
    if any(kw in lower for kw in ["must", "shall", "required", "mandatory"]):
        return "HIGH"
    if any(kw in lower for kw in ["should", "recommended"]):
        return "MEDIUM"
    return "LOW"


async def extract_from_handbook(
    text: str,
    *,
    document_title: str = "",
    scope_prefix: str = "",
) -> list[PolicyCandidate]:
    """Extract candidate rules from a policy handbook.

    Uses keyword-based extraction to find normative sentences and
    structural parsing to identify sections.

    Args:
        text: The handbook text (markdown or plain text).
        document_title: Title of the source document.
        scope_prefix: Scope prefix for extracted rules.

    Returns:
        List of PolicyCandidate objects.
    """
    candidates: list[PolicyCandidate] = []
    scope = [scope_prefix] if scope_prefix else []
    current_section = document_title

    # Split into lines and process
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Update current section from headings
        heading_match = _HEADING_PATTERN.match(stripped)
        if heading_match:
            current_section = heading_match.group(1).strip()
            continue
        num_heading = _NUMBERED_HEADING.match(stripped)
        if num_heading:
            current_section = num_heading.group(1).strip()
            continue

        # Check if line contains a normative statement
        is_normative = any(p.search(stripped) for p in _NORMATIVE_PATTERNS)
        if not is_normative:
            continue

        # Clean up the statement
        statement = stripped.lstrip("- ").lstrip("* ").lstrip("0123456789. ")
        if len(statement) < 15:
            continue

        candidates.append(
            PolicyCandidate(
                statement=statement[:500],
                section=current_section,
                modality=_detect_modality(statement),
                severity=_detect_severity(statement),
                scope=scope,
                rationale=f"Extracted from: {document_title} > {current_section}",
                confidence=0.5,
            )
        )

    logger.info(
        "policy_handbook_extracted",
        document_title=document_title,
        candidates=len(candidates),
        text_length=len(text),
    )
    return candidates
