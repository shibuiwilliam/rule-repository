"""Handbook extractor — extracts rules from employee handbooks and operational manuals.

More forgiving structure than regulations; uses section headings to organize
extracted rules. Detects HR-specific scope (employment type, position level)
and labor agreement references.
See CLAUDE.md §14.11, IMPROVEMENT.md §3 提案5.
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
    "てはならない",
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

# ---------------------------------------------------------------------------
# HR-specific scope detection
# ---------------------------------------------------------------------------

# Employment type patterns (雇用区分)
_EMPLOYMENT_TYPE_JP = re.compile(
    r"(正社員|正規社員|契約社員|パート(?:タイム)?|アルバイト|派遣社員|嘱託社員|臨時社員|非正規)"
)
_EMPLOYMENT_TYPE_EN = re.compile(
    r"(full[- ]?time|part[- ]?time|contract\s+employee|temporary|intern|probationary)",
    re.IGNORECASE,
)

# Position level patterns (職位)
_POSITION_LEVEL_JP = re.compile(r"(管理職|一般社員|役員|取締役|部長|課長|係長|主任|新入社員)")
_POSITION_LEVEL_EN = re.compile(
    r"(manager|executive|director|supervisor|officer|senior|junior|entry[- ]?level|lead)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Labor agreement reference patterns (労使協定)
# ---------------------------------------------------------------------------
_LABOR_AGREEMENT_JP = re.compile(r"(労使協定|三六協定|36協定|労働協約|就業規則|賃金規程|退職金規程|育児介護休業規程)")
_LABOR_AGREEMENT_EN = re.compile(
    r"(collective\s+(?:bargaining\s+)?agreement|labor\s+agreement|employment\s+regulations"
    r"|work\s+rules|salary\s+regulations|retirement\s+benefit\s+plan)",
    re.IGNORECASE,
)


class HandbookExtractor:
    """Extracts rules from employee handbooks and operational manuals.

    Unlike the regulation extractor, this handles less formal structure:
    section headings, bullet lists, and paragraph-level normative statements.
    Detects HR-specific scope (employment type, position level) and labor
    agreement references.
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
            if not _contains_normative(para):
                continue

            # Detect HR-specific scope
            employment_types = _detect_employment_types(para)
            position_levels = _detect_position_levels(para)
            labor_refs = _detect_labor_agreement_refs(para)

            # Also check the current section heading for scope clues
            if current_section:
                employment_types.update(_detect_employment_types(current_section))
                position_levels.update(_detect_position_levels(current_section))

            source_refs: dict[str, object] = {
                "document": str(source.path),
                "section": current_section,
            }
            if employment_types:
                source_refs["employment_types"] = sorted(employment_types)
            if position_levels:
                source_refs["position_levels"] = sorted(position_levels)
            if labor_refs:
                source_refs["labor_agreement_refs"] = sorted(labor_refs)

            # Build tags
            tags = ["handbook", "extracted"]
            if employment_types:
                tags.append("scoped_by_employment_type")
            if labor_refs:
                tags.append("labor_agreement_ref")

            candidates.append(
                CandidateRule(
                    statement=para[:500],
                    modality=_detect_modality(para),
                    severity=_detect_severity(para),
                    scope=source.metadata.get("scope", []),
                    source_refs=source_refs,
                    department=source.metadata.get("department", "hr"),
                    tags=tags,
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
    if any(kw in text for kw in ("してはならない", "てはならない", "禁止する")):
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


# ---------------------------------------------------------------------------
# HR-specific scope detection helpers
# ---------------------------------------------------------------------------


def _detect_employment_types(text: str) -> set[str]:
    """Detect employment type mentions in text."""
    found: set[str] = set()
    for m in _EMPLOYMENT_TYPE_JP.finditer(text):
        found.add(m.group(1))
    for m in _EMPLOYMENT_TYPE_EN.finditer(text):
        found.add(m.group(1).lower())
    return found


def _detect_position_levels(text: str) -> set[str]:
    """Detect position level mentions in text."""
    found: set[str] = set()
    for m in _POSITION_LEVEL_JP.finditer(text):
        found.add(m.group(1))
    for m in _POSITION_LEVEL_EN.finditer(text):
        found.add(m.group(1).lower())
    return found


def _detect_labor_agreement_refs(text: str) -> set[str]:
    """Detect labor agreement references in text."""
    found: set[str] = set()
    for m in _LABOR_AGREEMENT_JP.finditer(text):
        found.add(m.group(1))
    for m in _LABOR_AGREEMENT_EN.finditer(text):
        found.add(m.group(1).lower())
    return found
