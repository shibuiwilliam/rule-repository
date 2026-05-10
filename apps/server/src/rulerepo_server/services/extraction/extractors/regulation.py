"""Regulation extractor — handles regulation documents (employment regs, expense policies, etc.).

Detects 条/項/号 structure (or English Article/Section/Clause equivalents).
Auto-creates ``derives_from`` edges when downstream rules reference upstream ones.
See CLAUDE.md §14.11.
"""

from __future__ import annotations

import re

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)

# Japanese regulatory structure patterns
_JP_ARTICLE = re.compile(r"第(\d+)条")
_JP_PARAGRAPH = re.compile(r"第(\d+)項")
_JP_ITEM = re.compile(r"第(\d+)号")

# English regulatory structure patterns
_EN_ARTICLE = re.compile(r"Article\s+(\d+)", re.IGNORECASE)
_EN_SECTION = re.compile(r"Section\s+(\d+)", re.IGNORECASE)
_EN_CLAUSE = re.compile(r"Clause\s+(\d+)", re.IGNORECASE)


class RegulationExtractor:
    """Extracts rules from regulation documents.

    Preserves hierarchical structure (Article-Section-Clause) and
    detects normative statements (MUST, SHALL, etc.).
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

        candidates: list[CandidateRule] = []
        paragraphs = content.split("\n\n")

        current_article = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Detect article/section markers
            article_match = _JP_ARTICLE.search(para) or _EN_ARTICLE.search(para)
            if article_match:
                current_article = article_match.group(0)

            # Check for normative language
            if _is_normative(para):
                source_path = current_article
                paragraph_match = _JP_PARAGRAPH.search(para) or _EN_SECTION.search(para)
                if paragraph_match:
                    source_path = f"{current_article}.{paragraph_match.group(0)}"

                candidates.append(
                    CandidateRule(
                        statement=para[:500],
                        modality=_detect_modality(para),
                        severity="HIGH" if _is_mandatory(para) else "MEDIUM",
                        scope=source.metadata.get("scope", []),
                        source_refs={
                            "document": str(source.path),
                            "path": source_path,
                        },
                        department=source.metadata.get("department", "compliance"),
                        tags=["regulation", "extracted"],
                        applicable_subject_kinds=["transaction", "event", "document"],
                        confidence=0.7,
                    )
                )

        logger.info("regulation_extraction_complete", candidates=len(candidates))
        return candidates


def _is_normative(text: str) -> bool:
    """Check if text contains normative language."""
    normative_jp = ["しなければならない", "してはならない", "するものとする", "できる", "努めなければならない"]
    normative_en = ["shall", "must", "must not", "may not", "is required", "shall not"]
    text_lower = text.lower()
    return any(kw in text for kw in normative_jp) or any(kw in text_lower for kw in normative_en)


def _is_mandatory(text: str) -> bool:
    """Check if text uses mandatory language."""
    mandatory_jp = ["しなければならない", "してはならない"]
    mandatory_en = ["must", "shall", "must not", "shall not"]
    text_lower = text.lower()
    return any(kw in text for kw in mandatory_jp) or any(kw in text_lower for kw in mandatory_en)


def _detect_modality(text: str) -> str:
    """Detect the modality of a normative statement."""
    text_lower = text.lower()
    if "してはならない" in text or "must not" in text_lower or "shall not" in text_lower:
        return "MUST_NOT"
    if "しなければならない" in text or "must" in text_lower or "shall" in text_lower:
        return "MUST"
    if "するものとする" in text or "should" in text_lower:
        return "SHOULD"
    if "できる" in text or "may" in text_lower:
        return "MAY"
    return "SHOULD"
