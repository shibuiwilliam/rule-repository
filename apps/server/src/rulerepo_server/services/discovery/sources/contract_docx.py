"""Contract DOCX ingestion — extracts clauses from Word documents.

Converts DOCX to PDF via subprocess (LibreOffice) before sending to
Gemini for clause-level extraction. Gemini does not parse DOCX directly.

Phase 7c. See: IMPROVEMENT.md §3.1
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ClauseCandidate:
    """A candidate clause extracted from a contract DOCX."""

    clause_id: str
    clause_type: str
    text: str
    heading: str = ""
    parent_clause_id: str | None = None
    confidence: float = 0.0


async def extract_from_docx(
    content: bytes,
    *,
    contract_type: str = "",
    counterparty: str = "",
) -> list[ClauseCandidate]:
    """Extract clauses from a contract DOCX file.

    Args:
        content: Raw DOCX bytes.
        contract_type: Type of contract (NDA, MSA, SOW, etc.).
        counterparty: Name of the counterparty.

    Returns:
        List of ClauseCandidate objects.
    """
    # TODO: Implement DOCX → PDF conversion + Gemini extraction
    # Steps: 1. Convert to PDF (LibreOffice subprocess)
    #        2. Sanitize PDF via pdf_sanitizer
    #        3. Upload to Gemini Files API
    #        4. Extract clauses with structured output
    logger.info(
        "contract_docx_extract_placeholder",
        contract_type=contract_type,
        counterparty=counterparty,
        content_size=len(content),
    )
    return []
