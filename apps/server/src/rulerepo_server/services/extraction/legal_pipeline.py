"""Legal document extraction pipeline — statute-aware rule extraction.

Stores source_refs as {statute_name, article, paragraph, item} and supports
nightly monitoring of configurable statute sources for changes.

Phase 7c. See: IMPROVEMENT.md §3.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.sources.regulation_pdf import (
    RegulationCandidate,
    extract_articles_from_text,
)

logger = get_logger(__name__)


@dataclass
class StatuteSource:
    """A monitored statute source for change detection."""

    name: str
    url: str
    jurisdiction: str = "jp"
    last_hash: str = ""
    scope_prefix: str = ""


@dataclass
class LegalExtractionResult:
    """Result of extracting rules from a legal document."""

    candidates: list[RegulationCandidate] = field(default_factory=list)
    source_refs: list[dict[str, str]] = field(default_factory=list)
    statute_name: str = ""
    jurisdiction: str = ""


async def extract_legal_document(
    text: str,
    *,
    statute_name: str,
    jurisdiction: str = "jp",
    scope_prefix: str = "",
) -> LegalExtractionResult:
    """Extract rules from a legal document with statute-aware source_refs.

    Args:
        text: The full text of the legal document.
        statute_name: Name of the statute (e.g., "Labor Standards Act").
        jurisdiction: ISO country code.
        scope_prefix: Scope prefix for the extracted rules.

    Returns:
        LegalExtractionResult with candidates and structured source_refs.
    """
    candidates = extract_articles_from_text(
        text,
        statute_name=statute_name,
        jurisdiction=jurisdiction,
        scope_prefix=scope_prefix,
    )

    source_refs = [
        {
            "statute_name": c.article_ref.statute_name,
            "article": c.article_ref.article,
            "paragraph": c.article_ref.paragraph or "",
            "item": c.article_ref.item or "",
        }
        for c in candidates
    ]

    logger.info(
        "legal_document_extracted",
        statute_name=statute_name,
        jurisdiction=jurisdiction,
        candidates=len(candidates),
    )

    return LegalExtractionResult(
        candidates=candidates,
        source_refs=source_refs,
        statute_name=statute_name,
        jurisdiction=jurisdiction,
    )


async def check_statute_changes(
    sources: list[StatuteSource],
) -> list[dict[str, Any]]:
    """Check monitored statute sources for changes.

    Compares current content hash against last_hash. Sources with changes
    are flagged for re-extraction.

    Args:
        sources: List of monitored statute sources.

    Returns:
        List of dicts describing detected changes.
    """
    changes: list[dict[str, Any]] = []

    for source in sources:
        # TODO: Fetch source.url and compute content hash
        # When hash differs from source.last_hash, flag for re-extraction
        # and identify affected rules via derives_from relationships
        logger.info(
            "statute_change_check",
            statute=source.name,
            url=source.url,
            note="Polling not yet implemented — requires HTTP fetch and hash comparison",
        )

    return changes
