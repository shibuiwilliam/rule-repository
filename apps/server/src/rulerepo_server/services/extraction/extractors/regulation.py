"""Regulation extractor — handles regulation documents (employment regs, expense policies, etc.).

Detects 条/項/号 structure (or English Article/Section/Clause equivalents).
Resolves forward/backward references (前項・前条, "preceding section").
Extracts statute numbers, effective periods, and amendment history.
Auto-creates ``derives_from`` edges when downstream rules reference upstream ones.
See CLAUDE.md §14.11, IMPROVEMENT.md §3 提案5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Japanese regulatory structure patterns
# ---------------------------------------------------------------------------
_JP_ARTICLE = re.compile(r"第(\d+)条")
_JP_PARAGRAPH = re.compile(r"第(\d+)項")
_JP_ITEM = re.compile(r"第(\d+)号")

# English regulatory structure patterns
_EN_ARTICLE = re.compile(r"Article\s+(\d+)", re.IGNORECASE)
_EN_SECTION = re.compile(r"Section\s+(\d+)", re.IGNORECASE)
_EN_CLAUSE = re.compile(r"Clause\s+(\d+)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Reference patterns (前項/前条 etc.)
# ---------------------------------------------------------------------------
_JP_PRECEDING_ARTICLE = re.compile(r"前条")
_JP_PRECEDING_PARAGRAPH = re.compile(r"前項")
_JP_FORWARD_ARTICLE = re.compile(r"次条")
_JP_CROSS_REF = re.compile(r"第(\d+)条(?:第(\d+)項)?(?:第(\d+)号)?")
_EN_PRECEDING = re.compile(r"the preceding (?:section|article|clause)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Statute number pattern (法律番号): e.g. "平成29年法律第45号" / "令和5年政令第12号"
# ---------------------------------------------------------------------------
_STATUTE_NUMBER = re.compile(r"((?:明治|大正|昭和|平成|令和)\d+年(?:法律|政令|省令|条例|規則)第\d+号)")

# ---------------------------------------------------------------------------
# Effective period / date patterns
# ---------------------------------------------------------------------------
_EFFECTIVE_DATE_JP = re.compile(
    r"(?:施行日|施行期日|適用日)[：:\s]*"  # noqa: RUF001
    r"(\d{4}年\d{1,2}月\d{1,2}日|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})"
)
_EFFECTIVE_DATE_EN = re.compile(
    r"(?:effective\s+date|commencement\s+date|enters?\s+into\s+(?:force|effect))"
    r"[:\s]*(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
    re.IGNORECASE,
)
_AMENDMENT_JP = re.compile(
    r"(?:改正|一部改正|全部改正)[：:\s]*"  # noqa: RUF001
    r"((?:明治|大正|昭和|平成|令和)\d+年\d{1,2}月\d{1,2}日)"
)
_AMENDMENT_EN = re.compile(
    r"(?:amended|revised|updated)\s+(?:on|as\s+of)\s+(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
    re.IGNORECASE,
)


@dataclass
class ResolvedRef:
    """A cross-reference within a regulation, resolved to a hierarchical path."""

    match_text: str
    target_path: str
    reference_type: str  # "internal", "preceding", "forward", "statute"


@dataclass
class RegulationMetadata:
    """Document-level metadata extracted from a regulation."""

    statute_numbers: list[str] = field(default_factory=list)
    effective_dates: list[str] = field(default_factory=list)
    amendment_dates: list[str] = field(default_factory=list)


class RegulationExtractor:
    """Extracts rules from regulation documents.

    Preserves hierarchical structure (Article-Section-Clause / 条-項-号)
    and detects normative statements (MUST, SHALL, etc.).
    Resolves intra-document references and extracts statute numbers.
    """

    source_types = ["regulation_doc", "regulation_pdf"]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from a regulation document.

        Args:
            source: The regulation document to process.

        Returns:
            List of CandidateRule with hierarchical source_refs.
        """
        content = source.content or ""
        if not content and source.path.exists():
            content = source.path.read_text(encoding="utf-8", errors="replace")

        logger.info("regulation_extraction_started", path=str(source.path), length=len(content))

        # Extract document-level metadata
        doc_meta = _extract_document_metadata(content)

        candidates: list[CandidateRule] = []
        paragraphs = content.split("\n\n")

        current_article = ""
        current_article_num = 0
        current_paragraph_num = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Detect article marker (条 / Article)
            article_match = _JP_ARTICLE.search(para) or _EN_ARTICLE.search(para)
            if article_match:
                current_article_num = int(article_match.group(1))
                current_article = article_match.group(0)
                current_paragraph_num = 0

            # Check for normative language
            if not _is_normative(para):
                continue

            # Build full hierarchical path: 条.項.号
            source_path = _build_hierarchy_path(
                para,
                current_article,
                current_article_num,
                current_paragraph_num,
            )

            # Update paragraph counter for the current article
            paragraph_match = _JP_PARAGRAPH.search(para) or _EN_SECTION.search(para)
            if paragraph_match:
                current_paragraph_num = int(paragraph_match.group(1))

            # Resolve references within this paragraph
            refs = _resolve_references(para, current_article_num, current_paragraph_num)

            # Build tags including statute numbers
            tags = ["regulation", "extracted"]
            if doc_meta.statute_numbers:
                tags.append("statutory")

            # Build source_refs
            source_refs: dict[str, object] = {
                "document": str(source.path),
                "path": source_path,
            }
            if refs:
                source_refs["references"] = [
                    {"text": r.match_text, "target": r.target_path, "type": r.reference_type} for r in refs
                ]
            if doc_meta.statute_numbers:
                source_refs["statute_numbers"] = doc_meta.statute_numbers
            if doc_meta.effective_dates:
                source_refs["effective_dates"] = doc_meta.effective_dates
            if doc_meta.amendment_dates:
                source_refs["amendment_dates"] = doc_meta.amendment_dates

            candidates.append(
                CandidateRule(
                    statement=para[:500],
                    modality=_detect_modality(para),
                    severity="HIGH" if _is_mandatory(para) else "MEDIUM",
                    scope=source.metadata.get("scope", []),
                    source_refs=source_refs,
                    department=source.metadata.get("department", "compliance"),
                    tags=tags,
                    applicable_subject_kinds=["transaction", "event", "document"],
                    confidence=0.7,
                )
            )

        logger.info("regulation_extraction_complete", candidates=len(candidates))
        return candidates


# ---------------------------------------------------------------------------
# Hierarchy path builder
# ---------------------------------------------------------------------------


def _build_hierarchy_path(
    text: str,
    current_article: str,
    current_article_num: int,
    current_paragraph_num: int,
) -> str:
    """Build a hierarchical path for a normative paragraph.

    Produces paths like "第3条.第2項.第1号" or "Article 5.Section 2".

    Args:
        text: The paragraph text.
        current_article: Current article marker string.
        current_article_num: Current article number.
        current_paragraph_num: Current paragraph number (fallback).

    Returns:
        A dot-separated hierarchical path string.
    """
    parts: list[str] = []

    # Article level (条 / Article)
    if current_article:
        parts.append(current_article)

    # Paragraph level (項 / Section)
    paragraph_match = _JP_PARAGRAPH.search(text) or _EN_SECTION.search(text)
    if paragraph_match:
        parts.append(paragraph_match.group(0))

    # Item level (号 / Clause)
    item_match = _JP_ITEM.search(text) or _EN_CLAUSE.search(text)
    if item_match:
        parts.append(item_match.group(0))

    return ".".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------


def _resolve_references(
    text: str,
    current_article_num: int,
    current_paragraph_num: int,
) -> list[ResolvedRef]:
    """Resolve forward/backward and cross-references in a paragraph.

    Handles:
      - 前条 (preceding article) → target = 第{N-1}条
      - 前項 (preceding paragraph) → target = 第{current}条.第{M-1}項
      - 次条 (next article) → target = 第{N+1}条
      - Explicit cross-refs like 第5条第2項第3号
      - English "the preceding section/article"
    """
    refs: list[ResolvedRef] = []

    # 前条 — preceding article
    for m in _JP_PRECEDING_ARTICLE.finditer(text):
        target_num = current_article_num - 1
        target = f"第{target_num}条" if target_num > 0 else ""
        refs.append(
            ResolvedRef(
                match_text=m.group(0),
                target_path=target,
                reference_type="preceding",
            )
        )

    # 前項 — preceding paragraph
    for m in _JP_PRECEDING_PARAGRAPH.finditer(text):
        target_para = current_paragraph_num - 1
        if current_article_num > 0 and target_para > 0:
            target = f"第{current_article_num}条.第{target_para}項"
        elif current_article_num > 0:
            target = f"第{current_article_num}条"
        else:
            target = ""
        refs.append(
            ResolvedRef(
                match_text=m.group(0),
                target_path=target,
                reference_type="preceding",
            )
        )

    # 次条 — next article
    for m in _JP_FORWARD_ARTICLE.finditer(text):
        target_num = current_article_num + 1
        refs.append(
            ResolvedRef(
                match_text=m.group(0),
                target_path=f"第{target_num}条",
                reference_type="forward",
            )
        )

    # English "the preceding section/article"
    for m in _EN_PRECEDING.finditer(text):
        target_num = current_article_num - 1
        target = f"Article {target_num}" if target_num > 0 else ""
        refs.append(
            ResolvedRef(
                match_text=m.group(0),
                target_path=target,
                reference_type="preceding",
            )
        )

    # Explicit Japanese cross-references: 第N条第M項第L号
    for m in _JP_CROSS_REF.finditer(text):
        art_num = int(m.group(1))
        # Skip self-references (the article marker itself)
        if art_num == current_article_num and not m.group(2):
            continue
        parts = [f"第{art_num}条"]
        if m.group(2):
            parts.append(f"第{m.group(2)}項")
        if m.group(3):
            parts.append(f"第{m.group(3)}号")
        refs.append(
            ResolvedRef(
                match_text=m.group(0),
                target_path=".".join(parts),
                reference_type="internal",
            )
        )

    return refs


# ---------------------------------------------------------------------------
# Document-level metadata extraction
# ---------------------------------------------------------------------------


def _extract_document_metadata(content: str) -> RegulationMetadata:
    """Extract statute numbers, effective dates, and amendments from document header."""
    meta = RegulationMetadata()

    # Statute numbers (法律番号)
    for m in _STATUTE_NUMBER.finditer(content):
        if m.group(1) not in meta.statute_numbers:
            meta.statute_numbers.append(m.group(1))

    # Effective dates (施行日 / effective date)
    for m in _EFFECTIVE_DATE_JP.finditer(content):
        if m.group(1) not in meta.effective_dates:
            meta.effective_dates.append(m.group(1))
    for m in _EFFECTIVE_DATE_EN.finditer(content):
        if m.group(1) not in meta.effective_dates:
            meta.effective_dates.append(m.group(1))

    # Amendment dates (改正)
    for m in _AMENDMENT_JP.finditer(content):
        if m.group(1) not in meta.amendment_dates:
            meta.amendment_dates.append(m.group(1))
    for m in _AMENDMENT_EN.finditer(content):
        if m.group(1) not in meta.amendment_dates:
            meta.amendment_dates.append(m.group(1))

    return meta


# ---------------------------------------------------------------------------
# Normative language detection
# ---------------------------------------------------------------------------


def _is_normative(text: str) -> bool:
    """Check if text contains normative language."""
    normative_jp = [
        "しなければならない",
        "してはならない",
        "てはならない",
        "するものとする",
        "できる",
        "努めなければならない",
    ]
    normative_en = ["shall", "must", "must not", "may not", "is required", "shall not"]
    text_lower = text.lower()
    return any(kw in text for kw in normative_jp) or any(kw in text_lower for kw in normative_en)


def _is_mandatory(text: str) -> bool:
    """Check if text uses mandatory language."""
    mandatory_jp = ["しなければならない", "してはならない", "てはならない"]
    mandatory_en = ["must", "shall", "must not", "shall not"]
    text_lower = text.lower()
    return any(kw in text for kw in mandatory_jp) or any(kw in text_lower for kw in mandatory_en)


def _detect_modality(text: str) -> str:
    """Detect the modality of a normative statement."""
    text_lower = text.lower()
    if "てはならない" in text or "must not" in text_lower or "shall not" in text_lower:
        return "MUST_NOT"
    if "しなければならない" in text or "must" in text_lower or "shall" in text_lower:
        return "MUST"
    if "するものとする" in text or "should" in text_lower:
        return "SHOULD"
    if "できる" in text or "may" in text_lower:
        return "MAY"
    return "SHOULD"
