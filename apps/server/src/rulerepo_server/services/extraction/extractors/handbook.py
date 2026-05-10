"""Handbook extractor — extracts rules from employee handbooks and operational manuals.

More forgiving structure than regulations; uses section headings to organize
extracted rules. See CLAUDE.md §14.11.
"""

from __future__ import annotations

import re

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)

# Section heading patterns
_HEADING_PATTERNS = [
    re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE),  # Markdown headings
    re.compile(r"^第\d+章\s+(.+)$", re.MULTILINE),  # Japanese chapter headings
    re.compile(r"^Chapter\s+\d+[.:]\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Section\s+\d+[.:]\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE),  # Numbered sections
]

# Normative language indicators
_NORMATIVE_JP = [
    "しなければならない",
    "してはならない",
    "するものとする",
    "禁止する",
    "義務とする",
    "遵守する",
    "努めなければならない",
]
_NORMATIVE_EN = [
    "must",
    "shall",
    "must not",
    "shall not",
    "is required",
    "is prohibited",
    "employees are expected to",
    "it is mandatory",
]


class HandbookExtractor:
    """Extracts rules from employee handbooks and operational manuals.

    Unlike the regulation extractor, this handles less formal structure:
    section headings, bullet lists, and paragraph-level normative statements.
    """

    source_types = ["handbook", "manual", "employee_handbook"]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from a handbook document.

        Args:
            source: The handbook source file.

        Returns:
            List of CandidateRule organized by section.
        """
        content = source.content or ""
        if not content and source.path.exists():
            content = source.path.read_text(encoding="utf-8", errors="replace")

        logger.info("handbook_extraction_started", path=str(source.path), length=len(content))

        candidates: list[CandidateRule] = []
        current_section = ""

        # Split into paragraphs
        paragraphs = re.split(r"\n\s*\n", content)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this paragraph is a heading
            heading = _extract_heading(para)
            if heading:
                current_section = heading
                continue

            # Check for normative language
            if _contains_normative(para):
                candidates.append(
                    CandidateRule(
                        statement=para[:500],
                        modality=_detect_modality(para),
                        severity=_detect_severity(para),
                        scope=source.metadata.get("scope", []),
                        source_refs={
                            "document": str(source.path),
                            "section": current_section,
                        },
                        department=source.metadata.get("department", "hr"),
                        tags=["handbook", "extracted"],
                        context=f"Section: {current_section}" if current_section else "",
                        applicable_subject_kinds=["event", "transaction", "document"],
                        confidence=0.6,
                    )
                )

        logger.info("handbook_extraction_complete", candidates=len(candidates))
        return candidates


def _extract_heading(text: str) -> str | None:
    """Extract a section heading from text, or None."""
    for pattern in _HEADING_PATTERNS:
        match = pattern.match(text.strip())
        if match:
            return match.group(1).strip()
    return None


def _contains_normative(text: str) -> bool:
    """Check if text contains normative language."""
    text_lower = text.lower()
    return any(kw in text for kw in _NORMATIVE_JP) or any(kw in text_lower for kw in _NORMATIVE_EN)


def _detect_modality(text: str) -> str:
    """Detect the modality of a normative statement."""
    text_lower = text.lower()
    if any(kw in text for kw in ("してはならない", "禁止する")):
        return "MUST_NOT"
    if "must not" in text_lower or "shall not" in text_lower or "is prohibited" in text_lower:
        return "MUST_NOT"
    if any(kw in text for kw in ("しなければならない", "義務とする")):
        return "MUST"
    if "must" in text_lower or "shall" in text_lower or "is required" in text_lower:
        return "MUST"
    if "するものとする" in text or "should" in text_lower or "is expected" in text_lower:
        return "SHOULD"
    if "努めなければならない" in text:
        return "SHOULD"
    return "SHOULD"


def _detect_severity(text: str) -> str:
    """Detect severity from context clues."""
    high_indicators = ["禁止", "prohibited", "terminate", "dismiss", "legal", "法的"]
    text_lower = text.lower()
    if any(kw in text or kw in text_lower for kw in high_indicators):
        return "HIGH"
    return "MEDIUM"
