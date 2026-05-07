"""Regulation PDF ingestion — extracts rules from regulatory documents.

Parses chapter/article/paragraph/item structure from PDFs. When a Gemini
client is available, uses the Files API with media_resolution_medium for
OCR and structural parsing. Without Gemini, falls back to text extraction
via the standard extraction pipeline.

Phase 7c. See: CLAUDE.md §9.4
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ArticleRef:
    """Reference to a specific article/paragraph in a regulation."""

    statute_name: str
    article: str
    paragraph: str | None = None
    item: str | None = None


@dataclass
class RegulationCandidate:
    """A candidate rule extracted from a regulation PDF."""

    statement: str
    article_ref: ArticleRef
    modality: str = "MUST"
    severity: str = "HIGH"
    scope: list[str] = field(default_factory=list)
    rationale: str = ""
    context: str = ""
    confidence: float = 0.0


# Article detection patterns for Japanese and Western regulations
_JP_ARTICLE = re.compile(r"第(\d+)条(?:の(\d+))?")
_JP_PARAGRAPH = re.compile(r"(\d+)\s")
_WESTERN_ARTICLE = re.compile(r"(?:Article|Section|Rule)\s+(\d+)(?:\.(\d+))?", re.IGNORECASE)

# Modality detection keywords
_MUST_KEYWORDS = ["shall", "must", "しなければならない", "なければならない", "ものとする", "義務"]
_MUST_NOT_KEYWORDS = ["shall not", "must not", "してはならない", "禁止", "prohibited"]
_SHOULD_KEYWORDS = ["should", "するよう努め", "努力", "望ましい", "recommended"]


def _detect_modality(text: str) -> str:
    """Detect the normative modality of a text fragment."""
    lower = text.lower()
    for kw in _MUST_NOT_KEYWORDS:
        if kw in lower or kw in text:
            return "MUST_NOT"
    for kw in _MUST_KEYWORDS:
        if kw in lower or kw in text:
            return "MUST"
    for kw in _SHOULD_KEYWORDS:
        if kw in lower or kw in text:
            return "SHOULD"
    return "MUST"


def extract_articles_from_text(
    text: str,
    *,
    statute_name: str = "",
    jurisdiction: str = "jp",
    scope_prefix: str = "",
) -> list[RegulationCandidate]:
    """Extract candidate rules from regulation text (non-LLM fallback).

    Parses Japanese (第N条) and Western (Article N) article structures,
    detects modality from keywords, and generates candidates.

    Args:
        text: The regulation text (extracted from PDF or provided directly).
        statute_name: Name of the statute for source_refs.
        jurisdiction: ISO country code.
        scope_prefix: Scope prefix (e.g., "hr/attendance").

    Returns:
        List of RegulationCandidate objects.
    """
    candidates: list[RegulationCandidate] = []
    lines = text.split("\n")
    current_article: str | None = None
    current_text: list[str] = []
    scope = [scope_prefix] if scope_prefix else [f"compliance/{jurisdiction}"]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for Japanese article
        jp_match = _JP_ARTICLE.match(stripped)
        # Check for Western article
        west_match = _WESTERN_ARTICLE.match(stripped)

        if jp_match or west_match:
            # Flush previous article
            if current_article and current_text:
                body = " ".join(current_text)
                if len(body) > 20:  # Skip trivially short articles
                    candidates.append(
                        RegulationCandidate(
                            statement=body[:500],
                            article_ref=ArticleRef(
                                statute_name=statute_name,
                                article=current_article,
                            ),
                            modality=_detect_modality(body),
                            scope=scope,
                            context=body,
                            confidence=0.6,
                        )
                    )
                current_text = []

            if jp_match:
                current_article = jp_match.group(1)
                remainder = stripped[jp_match.end() :].strip()
                if remainder:
                    current_text.append(remainder)
            elif west_match:
                current_article = west_match.group(1)
                remainder = stripped[west_match.end() :].strip()
                if remainder:
                    current_text.append(remainder)
        else:
            current_text.append(stripped)

    # Flush last article
    if current_article and current_text:
        body = " ".join(current_text)
        if len(body) > 20:
            candidates.append(
                RegulationCandidate(
                    statement=body[:500],
                    article_ref=ArticleRef(
                        statute_name=statute_name,
                        article=current_article,
                    ),
                    modality=_detect_modality(body),
                    scope=scope,
                    context=body,
                    confidence=0.6,
                )
            )

    logger.info(
        "regulation_text_extracted",
        statute_name=statute_name,
        candidates=len(candidates),
    )
    return candidates


async def extract_from_pdf(
    content: bytes,
    *,
    statute_name: str = "",
    jurisdiction: str = "jp",
    scope_prefix: str = "",
    gemini_client: Any | None = None,
) -> list[RegulationCandidate]:
    """Extract candidate rules from a regulation PDF.

    When gemini_client is provided, uses the Files API with
    media_resolution_medium. Otherwise falls back to text extraction.

    Args:
        content: Raw PDF bytes.
        statute_name: Name of the statute for source_refs.
        jurisdiction: ISO country code.
        scope_prefix: Scope prefix (e.g., "hr/attendance").
        gemini_client: Optional Gemini client for LLM-powered extraction.

    Returns:
        List of RegulationCandidate objects.
    """
    if gemini_client is not None:
        # LLM-powered extraction via Gemini Files API
        try:
            from google.genai import types

            response = gemini_client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[
                    types.Part.from_bytes(data=content, mime_type="application/pdf"),
                    "Extract all normative rules from this regulation. For each rule, provide: "
                    "the article number, the rule statement, the modality (MUST/MUST_NOT/SHOULD/MAY), "
                    "and a brief rationale. Return as JSON array.",
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    media_resolution="media_resolution_medium",
                ),
            )
            import json

            results = json.loads(response.text or "[]")
            candidates = []
            scope = [scope_prefix] if scope_prefix else [f"compliance/{jurisdiction}"]
            for item in results:
                candidates.append(
                    RegulationCandidate(
                        statement=item.get("statement", ""),
                        article_ref=ArticleRef(
                            statute_name=statute_name,
                            article=str(item.get("article", "")),
                        ),
                        modality=item.get("modality", "MUST"),
                        scope=scope,
                        rationale=item.get("rationale", ""),
                        confidence=0.8,
                    )
                )
            logger.info(
                "regulation_pdf_gemini_extracted",
                statute_name=statute_name,
                candidates=len(candidates),
            )
            return candidates
        except Exception as exc:
            logger.warning("regulation_pdf_gemini_failed", error=str(exc))
            # Fall through to text extraction

    # Fallback: try to extract text from PDF
    try:
        import io

        import pikepdf

        pdf = pikepdf.Pdf.open(io.BytesIO(content))
        text_parts = []
        for page in pdf.pages:
            text_parts.append(page.extract_text() if hasattr(page, "extract_text") else "")
        pdf.close()
        text = "\n".join(text_parts)
    except Exception:
        # If pikepdf can't extract text, return empty
        logger.warning("regulation_pdf_text_extraction_failed", content_size=len(content))
        return []

    return extract_articles_from_text(
        text,
        statute_name=statute_name,
        jurisdiction=jurisdiction,
        scope_prefix=scope_prefix,
    )
