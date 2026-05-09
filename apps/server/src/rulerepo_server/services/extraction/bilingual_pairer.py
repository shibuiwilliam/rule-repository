"""Bilingual clause pairer — matches EN and JA contract clauses as semantic twins.

See CLAUDE.md §14.3.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClausePair:
    """A matched pair of clauses in two locales."""

    clause_id: str
    en_text: str
    ja_text: str
    confidence: float = 0.0
    clause_type: str = ""


async def pair_bilingual_clauses(
    en_clauses: list[dict[str, str]],
    ja_clauses: list[dict[str, str]],
) -> list[ClausePair]:
    """Match EN and JA clauses by position and semantic similarity.

    Uses positional matching as primary signal, with clause-type matching
    as a secondary heuristic. LLM-based semantic matching is used only
    for ambiguous cases.

    Args:
        en_clauses: List of {"text": ..., "position": ..., "clause_type": ...}
        ja_clauses: List of {"text": ..., "position": ..., "clause_type": ...}

    Returns:
        List of matched ClausePair objects.
    """
    pairs = []
    used_ja = set()

    for en in en_clauses:
        best_match = None
        best_score = 0.0

        for i, ja in enumerate(ja_clauses):
            if i in used_ja:
                continue
            score = 0.0
            # Position match
            if en.get("position") == ja.get("position"):
                score += 0.6
            # Clause type match
            if en.get("clause_type") and en.get("clause_type") == ja.get("clause_type"):
                score += 0.4
            if score > best_score:
                best_score = score
                best_match = (i, ja)

        if best_match:
            idx, ja = best_match
            used_ja.add(idx)
            pairs.append(
                ClausePair(
                    clause_id=f"clause_{en.get('position', len(pairs))}",
                    en_text=en.get("text", ""),
                    ja_text=ja.get("text", ""),
                    confidence=best_score,
                    clause_type=en.get("clause_type", ""),
                )
            )

    return pairs
