"""Handbook extractor — extracts rules from HR handbook PDFs and text.

Parses HR handbooks (employee manuals, policy documents) to identify
normative statements about attendance, leave, compensation, conduct,
and other HR topics. Produces candidate rules for human review.

See: CLAUDE.md SS16.2
"""

from __future__ import annotations

import re
from typing import Any

# Section heading patterns common in HR handbooks
_SECTION_RE = re.compile(
    r"^(?:(?:Chapter|Section|Article|Part|Item)\s+\d+[\.:]\s*|"
    r"\d+[\.:]\d*[\.:]*\s*|"
    r"#{1,4}\s+)"
    r"(.+)$",
    re.IGNORECASE | re.MULTILINE,
)

# Patterns for normative HR statements
_NORMATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(must|shall|is required to|are required to)\b", re.IGNORECASE),
    re.compile(r"\b(must not|shall not|is prohibited|are prohibited|is not permitted)\b", re.IGNORECASE),
    re.compile(r"\b(should|is encouraged to|are encouraged to|is expected to)\b", re.IGNORECASE),
    re.compile(r"\b(may|is allowed to|are allowed to|is permitted to)\b", re.IGNORECASE),
]

# HR topic detection from section headings and content
_TOPIC_SCOPE_MAP: dict[str, list[str]] = {
    "attendance": ["hr/attendance"],
    "working hours": ["hr/attendance"],
    "overtime": ["hr/attendance", "hr/overtime"],
    "leave": ["hr/leave"],
    "vacation": ["hr/leave"],
    "holiday": ["hr/leave"],
    "paid time off": ["hr/leave"],
    "pto": ["hr/leave"],
    "sick leave": ["hr/leave"],
    "maternity": ["hr/leave", "hr/family"],
    "paternity": ["hr/leave", "hr/family"],
    "childcare": ["hr/leave", "hr/family"],
    "compensation": ["hr/compensation"],
    "salary": ["hr/compensation"],
    "bonus": ["hr/compensation"],
    "benefits": ["hr/benefits"],
    "insurance": ["hr/benefits"],
    "retirement": ["hr/benefits"],
    "pension": ["hr/benefits"],
    "conduct": ["hr/conduct"],
    "harassment": ["hr/conduct", "hr/compliance"],
    "discrimination": ["hr/conduct", "hr/compliance"],
    "disciplinary": ["hr/conduct", "hr/disciplinary"],
    "termination": ["hr/termination"],
    "resignation": ["hr/termination"],
    "hiring": ["hr/hiring"],
    "recruitment": ["hr/hiring"],
    "probation": ["hr/hiring"],
    "training": ["hr/training"],
    "evaluation": ["hr/performance"],
    "performance": ["hr/performance"],
    "remote work": ["hr/remote"],
    "telecommuting": ["hr/remote"],
    "travel": ["hr/travel"],
    "expense": ["hr/expenses", "finance/expenses"],
    "safety": ["hr/safety"],
    "health": ["hr/safety"],
    "confidentiality": ["hr/confidentiality"],
    "intellectual property": ["hr/ip"],
    "conflict of interest": ["hr/compliance"],
    "side business": ["hr/compliance"],
}


def _detect_modality(sentence: str) -> str:
    """Detect modality from a sentence.

    Args:
        sentence: The sentence to analyze.

    Returns:
        Modality string (MUST, MUST_NOT, SHOULD, MAY).
    """
    lower = sentence.lower()
    if any(kw in lower for kw in ("must not", "shall not", "prohibited", "not permitted")):
        return "MUST_NOT"
    if any(kw in lower for kw in ("must", "shall", "required")):
        return "MUST"
    if any(kw in lower for kw in ("should", "encouraged", "expected")):
        return "SHOULD"
    if any(kw in lower for kw in ("may", "allowed", "permitted")):
        return "MAY"
    return "SHOULD"


def _detect_severity(sentence: str, modality: str) -> str:
    """Detect severity from a sentence and its modality.

    Args:
        sentence: The sentence text.
        modality: The detected modality.

    Returns:
        Severity string.
    """
    lower = sentence.lower()
    if any(kw in lower for kw in ("criminal", "terminate", "dismissal", "illegal")):
        return "CRITICAL"
    if modality in ("MUST", "MUST_NOT"):
        if any(kw in lower for kw in ("safety", "harassment", "discrimination", "compliance")):
            return "HIGH"
        return "MEDIUM"
    return "LOW"


def _detect_scopes(heading: str, sentence: str) -> list[str]:
    """Detect HR scopes from section heading and sentence content.

    Args:
        heading: The section heading.
        sentence: The sentence text.

    Returns:
        List of scope strings.
    """
    scopes: set[str] = set()
    combined = (heading + " " + sentence).lower()

    for topic, topic_scopes in _TOPIC_SCOPE_MAP.items():
        if topic in combined:
            scopes.update(topic_scopes)

    if not scopes:
        scopes.add("hr")

    return sorted(scopes)


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences, handling common abbreviations.

    Args:
        text: Text to split.

    Returns:
        List of sentence strings.
    """
    # Protect common abbreviations from splitting
    protected = text.replace("e.g.", "e_g_").replace("i.e.", "i_e_").replace("etc.", "etc_")
    protected = re.sub(r"(\d)\.", r"\1_DOT_", protected)

    sentences = re.split(r"[.!?]\s+", protected)

    result: list[str] = []
    for s in sentences:
        restored = s.replace("e_g_", "e.g.").replace("i_e_", "i.e.").replace("etc_", "etc.")
        restored = re.sub(r"(\d)_DOT_", r"\1.", restored)
        stripped = restored.strip()
        if stripped:
            result.append(stripped)

    return result


def _is_normative(sentence: str) -> bool:
    """Check if a sentence contains normative language.

    Args:
        sentence: The sentence to check.

    Returns:
        True if the sentence is normative.
    """
    return any(p.search(sentence) for p in _NORMATIVE_PATTERNS)


class HandbookExtractor:
    """Extracts rule candidates from HR handbook documents.

    Parses PDF text or plain text content from employee handbooks,
    identifies normative statements about HR policies, and produces
    structured rule candidates with appropriate modality, severity,
    and scope.
    """

    @property
    def name(self) -> str:
        return "handbook"

    @property
    def domain(self) -> str:
        return "hr"

    @property
    def supported_source_types(self) -> list[str]:
        return ["pdf", "text", "markdown", "handbook"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract rule candidates from an HR handbook.

        Args:
            content: Raw bytes of the handbook (text or pre-extracted PDF text).
            source_type: Source type ('pdf', 'text', 'markdown', 'handbook').
            metadata: Additional metadata (filename, organization, jurisdiction, ...).

        Returns:
            List of candidate rule dicts.
        """
        text = content.decode("utf-8", errors="replace")
        jurisdiction = metadata.get("jurisdiction", "global")
        filename = metadata.get("filename", "handbook")

        sections = self._parse_sections(text)
        candidates: list[dict[str, Any]] = []

        for heading, section_text in sections:
            sentences = _split_into_sentences(section_text)
            for sentence in sentences:
                if not _is_normative(sentence):
                    continue
                if len(sentence) < 20:
                    continue

                modality = _detect_modality(sentence)
                severity = _detect_severity(sentence, modality)
                scopes = _detect_scopes(heading, sentence)

                candidates.append(
                    {
                        "statement": sentence,
                        "modality": modality,
                        "severity": severity,
                        "scope": scopes,
                        "jurisdiction": jurisdiction,
                        "rationale": (
                            f"Extracted from HR handbook section '{heading}' "
                            f"in {filename}. Normative statement identified "
                            f"for formalization."
                        ),
                        "source": {
                            "type": source_type,
                            "filename": filename,
                            "section": heading,
                            "original_text": sentence,
                        },
                        "tags": ["auto-extracted", "handbook", "hr"],
                        "applicable_subject_types": ["event"],
                    }
                )

        return candidates

    @staticmethod
    def _parse_sections(text: str) -> list[tuple[str, str]]:
        """Parse text into (heading, content) sections.

        Args:
            text: Full document text.

        Returns:
            List of (heading, content) tuples.
        """
        sections: list[tuple[str, str]] = []
        current_heading = "General"
        current_lines: list[str] = []

        for line in text.split("\n"):
            match = _SECTION_RE.match(line.strip())
            if match:
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines)))
                current_heading = match.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines)))

        return sections
