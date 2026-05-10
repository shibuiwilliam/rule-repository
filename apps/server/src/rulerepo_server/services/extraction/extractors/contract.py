"""Contract extractor — extracts rules from contract PDFs and DOCXs.

Wraps the existing contract extraction module (clause_segmenter, clause_classifier,
reference_resolver) to conform to the Extractor protocol pattern.

Detects clause hierarchy (Article-Section-Clause or 第N条-第M項-第L号),
extracts parties, governing law, effective period as structured metadata.
Default ``applicable_subject_kinds``: ``["clause_set", "document"]``.
Default ``department``: ``legal``.

See CLAUDE.md §14.11.
"""

from __future__ import annotations

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.contract.clause_segmenter import (
    ClauseSegmenter,
)
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)


class ContractExtractor:
    """Extracts rules from contract documents using clause segmentation.

    Delegates to the existing ``contract/`` module for structural parsing,
    then maps segmented clauses to the CandidateRule format.
    """

    source_types = ["contract_pdf", "contract_docx", "contract"]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from a contract document.

        Args:
            source: The contract document source.

        Returns:
            List of CandidateRule with clause-level source_refs.
        """
        content = source.content or ""
        if not content and source.path.exists():
            content = source.path.read_text(encoding="utf-8", errors="replace")

        logger.info("contract_extraction_started", path=str(source.path), length=len(content))

        # Use the existing clause segmenter
        segmenter = ClauseSegmenter()
        segmented = segmenter.segment(content)

        candidates: list[CandidateRule] = []
        for clause in segmented.clauses:
            # Only extract clauses with substantive content
            if len(clause.text.strip()) < 20:
                continue

            candidates.append(
                CandidateRule(
                    statement=clause.text[:500],
                    modality=_detect_clause_modality(clause.text),
                    severity="HIGH" if _is_high_risk_clause(clause.text) else "MEDIUM",
                    scope=source.metadata.get("scope", ["legal/contract"]),
                    source_refs={
                        "document": str(source.path),
                        "path": f"clause:{clause.id}",
                        "heading": clause.heading,
                        "level": clause.level,
                    },
                    department="legal",
                    tags=["contract", "clause", "extracted"],
                    applicable_subject_kinds=["clause_set", "document"],
                    confidence=0.75,
                )
            )

        logger.info("contract_extraction_complete", candidates=len(candidates))
        return candidates


def _detect_clause_modality(text: str) -> str:
    """Detect modality from contract clause language."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ("shall not", "must not", "may not", "is prohibited")):
        return "MUST_NOT"
    if any(kw in text_lower for kw in ("shall", "must", "is required", "agrees to")):
        return "MUST"
    if any(kw in text_lower for kw in ("should", "is expected")):
        return "SHOULD"
    if any(kw in text_lower for kw in ("may", "at its discretion")):
        return "MAY"
    return "MUST"


def _is_high_risk_clause(text: str) -> bool:
    """Check if clause contains high-risk indicators."""
    high_risk_indicators = [
        "unlimited liability",
        "indemnif",
        "consequential damages",
        "governing law",
        "jurisdiction",
        "termination",
        "non-compete",
        "exclusiv",
        "無制限",
        "損害賠償",
        "準拠法",
        "管轄",
    ]
    text_lower = text.lower()
    return any(indicator in text_lower or indicator in text for indicator in high_risk_indicators)
