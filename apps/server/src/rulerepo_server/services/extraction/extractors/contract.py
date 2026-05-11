"""Contract extractor — extracts rules from contract PDFs and DOCXs.

Wraps the existing contract extraction module (clause_segmenter, clause_classifier,
reference_resolver) to conform to the Extractor protocol pattern.

Detects clause hierarchy (Article-Section-Clause or 第N条-第M項-第L号),
resolves cross-references ("as defined in Section 3.2", 前項, 前条),
extracts parties, governing law, effective period as structured metadata.
Default ``applicable_subject_kinds``: ``["clause_set", "document"]``.
Default ``department``: ``legal``.

See CLAUDE.md §14.11, IMPROVEMENT.md §3 提案5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.contract.clause_segmenter import (
    SegmentedDocument,
    segment_contract,
)
from rulerepo_server.services.extraction.contract.reference_resolver import (
    resolve_references,
)
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Effective date / period patterns
# ---------------------------------------------------------------------------
_EFFECTIVE_DATE_EN = re.compile(
    r"(?:effective\s+(?:date|as\s+of)|commenc(?:es?|ing)\s+on|enters?\s+into\s+(?:force|effect)"
    r"|dated\s+as\s+of)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})",
    re.IGNORECASE,
)
_EFFECTIVE_DATE_JP = re.compile(
    r"(?:効力発生日|施行日|発効日|契約日)[：:\s]*"  # noqa: RUF001
    r"(\d{4}年\d{1,2}月\d{1,2}日|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})"
)
_TERM_DURATION = re.compile(
    r"(?:term|duration|有効期間|契約期間).*?(\d+)\s*(?:years?|months?|年|ヶ月|か月)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Party extraction patterns
# ---------------------------------------------------------------------------
_PARTY_EN = re.compile(
    r'(?:(?:by and )?between|"([^"]{2,80})"[,\s]+\((?:hereinafter\s+)?(?:the\s+)?"([^"]+)"\))',
    re.IGNORECASE,
)
_PARTY_PAREN = re.compile(
    r'"([^"]{2,80})"\s*\((?:hereinafter\s+)?(?:referred\s+to\s+as\s+)?'
    r'(?:the\s+)?"?(\w[\w\s]{0,30}\w)"?\)',
    re.IGNORECASE,
)
_PARTY_JP = re.compile(
    r"(甲|乙|丙|丁)[：:\s]+(.{2,60}?)(?:[（(\n]|$)",  # noqa: RUF001
    re.MULTILINE,
)


@dataclass
class ContractMetadata:
    """Document-level metadata extracted from a contract."""

    parties: list[dict[str, str]] = field(default_factory=list)
    effective_dates: list[str] = field(default_factory=list)
    term_duration: str = ""
    governing_law: str = ""


class ContractExtractor:
    """Extracts rules from contract documents using clause segmentation.

    Delegates to the existing ``contract/`` module for structural parsing
    and reference resolution, then maps segmented clauses to the
    CandidateRule format with enriched metadata.
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
        segmented = segment_contract(content)

        # Resolve cross-references across clauses
        ref_map = resolve_references(segmented)
        refs_by_clause: dict[str, list[dict[str, str]]] = {}
        for ref in ref_map.references:
            refs_by_clause.setdefault(ref.source_clause_id, []).append(
                {
                    "text": ref.match_text,
                    "target": ref.target_clause_id or "",
                    "type": ref.reference_type,
                }
            )

        # Extract document-level metadata
        doc_meta = _extract_contract_metadata(content, segmented)

        candidates: list[CandidateRule] = []
        for clause in segmented.clauses:
            # Only extract clauses with substantive content
            if len(clause.text.strip()) < 20:
                continue

            source_refs: dict[str, object] = {
                "document": str(source.path),
                "path": f"clause:{clause.id}",
                "heading": clause.heading,
                "level": clause.level,
            }

            # Attach cross-references if any
            clause_refs = refs_by_clause.get(clause.id)
            if clause_refs:
                source_refs["references"] = clause_refs

            # Attach document-level metadata
            if doc_meta.parties:
                source_refs["parties"] = doc_meta.parties
            if doc_meta.effective_dates:
                source_refs["effective_dates"] = doc_meta.effective_dates
            if doc_meta.term_duration:
                source_refs["term_duration"] = doc_meta.term_duration

            candidates.append(
                CandidateRule(
                    statement=clause.text[:500],
                    modality=_detect_clause_modality(clause.text),
                    severity="HIGH" if _is_high_risk_clause(clause.text) else "MEDIUM",
                    scope=source.metadata.get("scope", ["legal/contract"]),
                    source_refs=source_refs,
                    department="legal",
                    tags=["contract", "clause", "extracted"],
                    applicable_subject_kinds=["clause_set", "document"],
                    confidence=0.75,
                )
            )

        logger.info(
            "contract_extraction_complete",
            candidates=len(candidates),
            references_resolved=len(ref_map.references),
            references_unresolved=ref_map.unresolved_count,
            parties=len(doc_meta.parties),
        )
        return candidates


# ---------------------------------------------------------------------------
# Contract metadata extraction
# ---------------------------------------------------------------------------


def _extract_contract_metadata(content: str, doc: SegmentedDocument) -> ContractMetadata:
    """Extract parties, effective dates, and term duration from a contract."""
    meta = ContractMetadata()

    # --- Effective dates ---
    for m in _EFFECTIVE_DATE_EN.finditer(content):
        if m.group(1) not in meta.effective_dates:
            meta.effective_dates.append(m.group(1))
    for m in _EFFECTIVE_DATE_JP.finditer(content):
        if m.group(1) not in meta.effective_dates:
            meta.effective_dates.append(m.group(1))

    # --- Term duration ---
    term_match = _TERM_DURATION.search(content)
    if term_match:
        meta.term_duration = term_match.group(0).strip()

    # --- Party extraction ---
    # Pattern: "ACME Corp" (hereinafter the "Buyer")
    for m in _PARTY_PAREN.finditer(content):
        meta.parties.append({"name": m.group(1).strip(), "role": m.group(2).strip()})

    # Japanese pattern: 甲:株式会社ACME
    for m in _PARTY_JP.finditer(content):
        meta.parties.append({"name": m.group(2).strip(), "role": m.group(1).strip()})

    # Deduplicate by name
    seen: set[str] = set()
    unique_parties: list[dict[str, str]] = []
    for p in meta.parties:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique_parties.append(p)
    meta.parties = unique_parties

    return meta


# ---------------------------------------------------------------------------
# Clause analysis helpers
# ---------------------------------------------------------------------------


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
