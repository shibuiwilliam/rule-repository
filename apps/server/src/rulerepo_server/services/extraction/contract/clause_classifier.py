"""Clause classifier — identifies clause types within a contract.

Classifies each clause into a functional category (confidentiality,
payment, IP assignment, liability, termination, etc.) using keyword
heuristics. For higher accuracy, the LLM-based classifier should be used.

See: IMPROVEMENT.md §3.1, PROJECT.md §8.2.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.services.extraction.contract.clause_segmenter import Clause

# ---------------------------------------------------------------------------
# Clause type taxonomy
# ---------------------------------------------------------------------------

CLAUSE_TYPES = [
    "confidentiality",
    "payment",
    "ip_assignment",
    "liability",
    "indemnification",
    "termination",
    "term_duration",
    "governing_law",
    "dispute_resolution",
    "force_majeure",
    "representations",
    "data_protection",
    "non_compete",
    "non_solicitation",
    "assignment",
    "amendment",
    "notices",
    "general",
]


@dataclass(frozen=True)
class ClassifiedClause:
    """A clause with its predicted type and confidence."""

    clause: Clause
    clause_type: str
    confidence: float


# Keyword-based heuristic patterns (case-insensitive)
_KEYWORD_MAP: dict[str, list[str]] = {
    "confidentiality": ["confidential", "non-disclosure", "秘密", "nda", "proprietary"],
    "payment": ["payment", "fee", "invoice", "compensation", "支払", "対価"],
    "ip_assignment": ["intellectual property", "copyright", "patent", "license", "知的財産"],
    "liability": ["liability", "damages", "limitation of liability", "責任"],
    "indemnification": ["indemnif", "hold harmless", "補償"],
    "termination": ["terminat", "expiration", "cancel", "解除", "解約"],
    "term_duration": ["term", "duration", "effective date", "期間", "有効期間"],
    "governing_law": ["governing law", "jurisdiction", "準拠法", "裁判管轄"],
    "dispute_resolution": ["dispute", "arbitration", "mediation", "紛争"],
    "force_majeure": ["force majeure", "不可抗力"],
    "representations": ["represent", "warrant", "表明", "保証"],
    "data_protection": ["personal data", "privacy", "gdpr", "個人情報"],
    "non_compete": ["non-compete", "competitive", "競業"],
    "non_solicitation": ["non-solicitation", "solicit", "勧誘"],
    "assignment": ["assign", "transfer", "譲渡"],
    "amendment": ["amend", "modif", "変更"],
    "notices": ["notice", "notification", "通知"],
}


def classify_clause(clause: Clause) -> ClassifiedClause:
    """Classify a single clause by keyword matching.

    Args:
        clause: The clause to classify.

    Returns:
        A ClassifiedClause with the best-match type and confidence.
    """
    text_lower = (clause.heading + " " + clause.text).lower()
    best_type = "general"
    best_score = 0.0

    for clause_type, keywords in _KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_type = clause_type

    # Normalize confidence: 1 keyword match = 0.5, 2+ = 0.8+
    confidence = min(0.5 + (best_score - 1) * 0.15, 0.95) if best_score > 0 else 0.2

    return ClassifiedClause(clause=clause, clause_type=best_type, confidence=confidence)


def classify_all(clauses: list[Clause]) -> list[ClassifiedClause]:
    """Classify a list of clauses.

    Args:
        clauses: The clauses to classify.

    Returns:
        A list of ClassifiedClause results.
    """
    return [classify_clause(c) for c in clauses]
