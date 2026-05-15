"""PDF structure parser using Gemini File API.

Implements the two-call pattern per CLAUDE.md §14.5:
1. First call: extract section hierarchy as structured JSON
2. Second call: for each leaf section, extract normative sentences
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentSection:
    """A section extracted from a structured document."""

    section_id: str
    title: str
    level: int
    content: str
    page_range: tuple[int, int] | None = None
    parent_section_id: str | None = None
    children: list[DocumentSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuralExtractionResult:
    """Result of structural extraction from a document."""

    sections: list[DocumentSection]
    document_type: str = "unknown"
    language: str = "en"
    total_pages: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


async def extract_pdf_structure(
    content: bytes,
    *,
    filename: str = "document.pdf",
    language_hint: str | None = None,
) -> StructuralExtractionResult:
    """Extract hierarchical section structure from a PDF.

    Uses the Gemini File API with media_resolution_medium (560 tokens/page).
    For documents > a few pages, uploads via Files API (free, persists 48h).

    This is a stub implementation that returns an empty result.
    Full implementation requires a configured Gemini client.
    """
    logger.info("extract_pdf_structure", filename=filename, size=len(content))
    return StructuralExtractionResult(
        sections=[],
        document_type="pdf",
        language=language_hint or "en",
    )


async def extract_hierarchy_json(
    content: bytes,
    *,
    filename: str = "document.pdf",
) -> list[dict[str, Any]]:
    """First call: extract document section hierarchy as structured JSON.

    Returns a list of section descriptors with section IDs, titles,
    page ranges, and parent section IDs.

    Stub implementation — returns empty list.
    """
    return []


async def extract_normative_sentences(
    content: bytes,
    section: DocumentSection,
) -> list[dict[str, Any]]:
    """Second call: extract normative sentences from a leaf section.

    Returns sentences with cross-references resolved.

    Stub implementation — returns empty list.
    """
    return []
