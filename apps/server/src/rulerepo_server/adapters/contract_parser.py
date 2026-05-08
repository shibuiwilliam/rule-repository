"""Contract parser adapter — extracts structured clauses from DOCX, PDF, and text.

Delegates clause segmentation and classification to the extraction pipeline.
PDF parsing uses Gemini Files API for OCR; DOCX uses python-docx for text extraction.

See: CLAUDE.md §12.2, ADR 0004
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from rulerepo_server.domain.contract import ContractScope
from rulerepo_server.services.extraction.contract.clause_classifier import (
    ClassifiedClause,
    classify_all,
)
from rulerepo_server.services.extraction.contract.clause_segmenter import (
    SegmentedDocument,
    segment_contract,
)
from rulerepo_server.services.extraction.contract.reference_resolver import (
    ReferenceMap,
    resolve_references,
)


@dataclass
class ParsedContract:
    """A fully parsed contract with classified clauses and metadata.

    Attributes:
        document: The segmented document with raw clauses.
        classified_clauses: Clauses with detected types and confidence.
        references: Internal and external cross-references.
        scope: Contract metadata (type, governing law, etc.).
        source_format: Original format ("text", "docx", "pdf").
        raw_text: The raw extracted text before segmentation.
    """

    document: SegmentedDocument
    classified_clauses: list[ClassifiedClause] = field(default_factory=list)
    references: ReferenceMap | None = None
    scope: ContractScope = field(default_factory=ContractScope)
    source_format: str = "text"
    raw_text: str = ""

    @property
    def clause_count(self) -> int:
        """Number of clauses found."""
        return self.document.clause_count

    def to_evaluation_payload(self) -> dict[str, Any]:
        """Convert to the payload format expected by ClauseSetAdapter."""
        clauses_data = []
        for clause in self.document.clauses:
            classified = next(
                (c for c in self.classified_clauses if c.clause.id == clause.id),
                None,
            )
            clauses_data.append(
                {
                    "clause_id": clause.id,
                    "heading": clause.heading,
                    "text": clause.text,
                    "level": clause.level,
                    "clause_type": classified.clause_type if classified else "general",
                    "classification_confidence": classified.confidence if classified else 0.0,
                }
            )

        return {
            "contract_type": self.scope.contract_type or "other",
            "governing_law": self.scope.governing_law or "",
            "counterparty_country": self.scope.counterparty_country or "",
            "party_role": self.scope.party_role or "both",
            "language": self.scope.language or "en",
            "clauses": clauses_data,
            "clause_count": self.clause_count,
            "preamble": self.document.preamble,
        }


class ContractParser:
    """Parses contracts from text, DOCX, or PDF into structured clauses.

    Usage::

        parser = ContractParser()
        parsed = parser.parse_text(contract_text, scope=scope)
        # or
        parsed = await parser.parse_docx(docx_bytes, scope=scope)
    """

    def parse_text(
        self,
        text: str,
        *,
        title: str = "",
        scope: ContractScope | None = None,
    ) -> ParsedContract:
        """Parse a plain-text contract into structured clauses.

        Args:
            text: The contract text.
            title: Optional document title.
            scope: Contract metadata.

        Returns:
            A ParsedContract with segmented and classified clauses.
        """
        scope = scope or ContractScope()
        document = segment_contract(text, title=title)
        classified = classify_all(document.clauses)
        references = resolve_references(document)

        return ParsedContract(
            document=document,
            classified_clauses=classified,
            references=references,
            scope=scope,
            source_format="text",
            raw_text=text,
        )

    async def parse_docx(
        self,
        content: bytes,
        *,
        title: str = "",
        scope: ContractScope | None = None,
    ) -> ParsedContract:
        """Parse a DOCX file into structured clauses.

        Extracts text using python-docx, preserving paragraph structure
        and heading hierarchy.

        Args:
            content: Raw DOCX bytes.
            title: Optional document title override.
            scope: Contract metadata.

        Returns:
            A ParsedContract with segmented and classified clauses.
        """
        text = _extract_docx_text(content)
        parsed = self.parse_text(text, title=title, scope=scope)
        parsed.source_format = "docx"
        return parsed

    async def parse_pdf_text(
        self,
        text: str,
        *,
        title: str = "",
        scope: ContractScope | None = None,
    ) -> ParsedContract:
        """Parse pre-extracted PDF text into structured clauses.

        For actual PDF files, the caller should first extract text via
        Gemini Files API (see CLAUDE.md §9.5), then pass the result here.

        Args:
            text: Extracted text from a PDF.
            title: Optional document title.
            scope: Contract metadata.

        Returns:
            A ParsedContract with segmented and classified clauses.
        """
        parsed = self.parse_text(text, title=title, scope=scope)
        parsed.source_format = "pdf"
        return parsed


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX bytes, preserving paragraph structure.

    Falls back to empty string if python-docx is unavailable or the file
    is malformed.
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
            # Preserve heading styles as structural markers
            style_name = para.style.name if para.style else ""
            if style_name.startswith("Heading"):
                level_match = re.search(r"\d+", style_name)
                level = int(level_match.group()) if level_match else 1
                paragraphs.append(f"{'#' * level} {text}")
            else:
                paragraphs.append(text)

        return "\n\n".join(paragraphs)
    except ImportError:
        return ""
    except Exception:
        return ""
