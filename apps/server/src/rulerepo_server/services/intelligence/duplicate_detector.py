"""Duplicate and near-duplicate rule detection (RR-033).

Identifies rules that are semantically similar or identical,
helping maintain a clean corpus without redundancy.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DuplicatePair:
    """A pair of rules detected as duplicates or near-duplicates."""

    rule_id_a: str
    rule_id_b: str
    similarity: float  # 0-1
    method: str  # "exact", "near_duplicate", "semantic"
    statement_a: str = ""
    statement_b: str = ""


def find_duplicates(
    rules: list[dict],
    *,
    threshold: float = 0.85,
    max_pairs: int = 100,
) -> list[DuplicatePair]:
    """Find duplicate and near-duplicate rules in a corpus.

    Uses SequenceMatcher for text similarity. In production,
    this would also use embedding-based semantic similarity.

    Args:
        rules: List of rule dicts, each with at least "id" and "statement".
        threshold: Minimum similarity ratio to consider a near-duplicate.
        max_pairs: Maximum number of pairs to return.

    Returns:
        Sorted list of DuplicatePair (highest similarity first).
    """
    pairs: list[DuplicatePair] = []

    for i, rule_a in enumerate(rules):
        for j, rule_b in enumerate(rules):
            if j <= i:
                continue
            if len(pairs) >= max_pairs:
                break

            stmt_a = rule_a.get("statement", "")
            stmt_b = rule_b.get("statement", "")

            # Skip very short statements
            if len(stmt_a) < 10 or len(stmt_b) < 10:
                continue

            # Exact match
            if stmt_a.strip().lower() == stmt_b.strip().lower():
                pairs.append(
                    DuplicatePair(
                        rule_id_a=str(rule_a.get("id", "")),
                        rule_id_b=str(rule_b.get("id", "")),
                        similarity=1.0,
                        method="exact",
                        statement_a=stmt_a[:100],
                        statement_b=stmt_b[:100],
                    )
                )
                continue

            # Near-duplicate (text similarity)
            ratio = SequenceMatcher(None, stmt_a.lower(), stmt_b.lower()).ratio()
            if ratio >= threshold:
                pairs.append(
                    DuplicatePair(
                        rule_id_a=str(rule_a.get("id", "")),
                        rule_id_b=str(rule_b.get("id", "")),
                        similarity=round(ratio, 3),
                        method="near_duplicate",
                        statement_a=stmt_a[:100],
                        statement_b=stmt_b[:100],
                    )
                )

    logger.info("duplicate_scan_complete", rules=len(rules), pairs_found=len(pairs))
    return sorted(pairs, key=lambda p: p.similarity, reverse=True)
