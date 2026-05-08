"""Contract DOCX ingestion — extracts clauses from Word documents.

Uses python-docx for text extraction and the existing clause segmenter/
classifier pipeline for structured clause identification.

Phase 8. See: CLAUDE.md §12.2, ADR 0004
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

    Uses python-docx for text extraction, then the clause segmenter
    and classifier for structured identification.

    Args:
        content: Raw DOCX bytes.
        contract_type: Type of contract (NDA, MSA, SOW, etc.).
        counterparty: Name of the counterparty.

    Returns:
        List of ClauseCandidate objects.
    """
    text = _extract_text_from_docx(content)
    if not text:
        logger.warning(
            "contract_docx_no_text_extracted",
            contract_type=contract_type,
            content_size=len(content),
        )
        return []

    # Use the extraction pipeline's clause segmenter and classifier
    from rulerepo_server.services.extraction.contract.clause_classifier import classify_all
    from rulerepo_server.services.extraction.contract.clause_segmenter import segment_contract

    document = segment_contract(text, title=contract_type or "Contract")
    if document.clause_count == 0:
        logger.info(
            "contract_docx_no_clauses_found",
            contract_type=contract_type,
            text_length=len(text),
        )
        return []

    classified = classify_all(document.clauses)

    candidates: list[ClauseCandidate] = []
    for cc in classified:
        candidates.append(
            ClauseCandidate(
                clause_id=cc.clause.id,
                clause_type=cc.clause_type,
                text=cc.clause.text,
                heading=cc.clause.heading,
                parent_clause_id=cc.clause.parent_id,
                confidence=cc.confidence,
            )
        )

    logger.info(
        "contract_docx_extracted",
        contract_type=contract_type,
        clauses_found=len(candidates),
        counterparty=counterparty,
    )
    return candidates


def _extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx.

    Falls back to empty string if python-docx is unavailable.
    """
    try:
        import io

        from docx import Document  # type: ignore[import-untyped]

        doc = Document(io.BytesIO(content))
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            # Map heading styles to article-like format for the segmenter
            style_name = para.style.name if para.style else ""
            if style_name.startswith("Heading"):
                paragraphs.append(text)
            else:
                paragraphs.append(text)

        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("python_docx_not_available")
        return ""
    except Exception as exc:
        logger.warning("docx_extraction_failed", error=str(exc))
        return ""
