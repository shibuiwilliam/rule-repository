"""Contract comparator — semantic clause-level diffing.

Compares a draft contract's clauses against standard clauses (from rules)
or another contract, producing per-clause deviation reports.

See: CLAUDE.md §12.2, ADR 0004
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from rulerepo_server.services.extraction.contract.clause_segmenter import Clause


@dataclass(frozen=True)
class ClauseMatch:
    """A matched pair of clauses between draft and standard.

    Attributes:
        draft_clause_id: Clause ID from the draft contract.
        standard_clause_id: Clause ID from the standard contract or rule.
        draft_text: Text of the draft clause.
        standard_text: Text of the standard/reference clause.
        similarity: Textual similarity score (0.0 to 1.0).
        deviation_summary: Description of how the draft deviates from standard.
        risk_level: Deviation risk level ("low", "medium", "high").
    """

    draft_clause_id: str
    standard_clause_id: str
    draft_text: str
    standard_text: str
    similarity: float
    deviation_summary: str = ""
    risk_level: str = "low"


@dataclass(frozen=True)
class UnmatchedClause:
    """A clause in the draft that has no corresponding standard clause.

    Attributes:
        clause_id: The clause ID.
        clause_text: The clause text.
        clause_type: The classified clause type.
        source: Whether this is from the "draft" or the "standard".
    """

    clause_id: str
    clause_text: str
    clause_type: str = "general"
    source: str = "draft"


@dataclass
class ComparisonResult:
    """Result of comparing a draft contract against a standard.

    Attributes:
        matched_clauses: Clauses that were matched between draft and standard.
        unmatched_draft: Draft clauses with no standard match.
        missing_standard: Standard clauses missing from the draft.
        overall_similarity: Average similarity across matched clauses.
        high_risk_count: Number of high-risk deviations.
    """

    matched_clauses: list[ClauseMatch] = field(default_factory=list)
    unmatched_draft: list[UnmatchedClause] = field(default_factory=list)
    missing_standard: list[UnmatchedClause] = field(default_factory=list)

    @property
    def overall_similarity(self) -> float:
        """Average similarity of matched clauses."""
        if not self.matched_clauses:
            return 0.0
        return sum(m.similarity for m in self.matched_clauses) / len(self.matched_clauses)

    @property
    def high_risk_count(self) -> int:
        """Number of matched clauses with high-risk deviations."""
        return sum(1 for m in self.matched_clauses if m.risk_level == "high")


class ContractComparator:
    """Compares contract clauses against standard clauses.

    Uses text similarity for matching and deviation detection. For deeper
    semantic comparison, the caller should use the LLM provider to analyze
    matched pairs.

    Usage::

        comparator = ContractComparator()
        result = comparator.compare(draft_clauses, standard_clauses)
    """

    def __init__(self, *, similarity_threshold: float = 0.3) -> None:
        """Initialize comparator.

        Args:
            similarity_threshold: Minimum similarity for a clause pair to
                be considered a match. Default 0.3 (lenient, since clause
                types are used as primary matching).
        """
        self._threshold = similarity_threshold

    def compare(
        self,
        draft_clauses: list[Clause],
        standard_clauses: list[Clause],
        *,
        draft_types: dict[str, str] | None = None,
        standard_types: dict[str, str] | None = None,
    ) -> ComparisonResult:
        """Compare draft clauses against standard clauses.

        Matching strategy:
        1. Match by clause type first (when classified types are provided).
        2. For unmatched, fall back to text similarity.
        3. Report unmatched draft clauses and missing standard clauses.

        Args:
            draft_clauses: Clauses from the draft contract.
            standard_clauses: Clauses from the standard/reference contract.
            draft_types: Optional mapping of clause_id → clause_type for draft.
            standard_types: Optional mapping of clause_id → clause_type for standard.

        Returns:
            A ComparisonResult with per-clause analysis.
        """
        draft_types = draft_types or {}
        standard_types = standard_types or {}

        matched: list[ClauseMatch] = []
        used_standard_ids: set[str] = set()
        used_draft_ids: set[str] = set()

        # Phase 1: match by clause type
        for dc in draft_clauses:
            d_type = draft_types.get(dc.id, "")
            if not d_type or d_type == "general":
                continue

            for sc in standard_clauses:
                if sc.id in used_standard_ids:
                    continue
                s_type = standard_types.get(sc.id, "")
                if d_type == s_type:
                    sim = _text_similarity(dc.text, sc.text)
                    match = _make_match(dc, sc, sim)
                    matched.append(match)
                    used_standard_ids.add(sc.id)
                    used_draft_ids.add(dc.id)
                    break

        # Phase 2: fall back to text similarity for unmatched
        remaining_draft = [c for c in draft_clauses if c.id not in used_draft_ids]
        remaining_standard = [c for c in standard_clauses if c.id not in used_standard_ids]

        for dc in remaining_draft:
            best_match: Clause | None = None
            best_sim = 0.0

            for sc in remaining_standard:
                if sc.id in used_standard_ids:
                    continue
                sim = _text_similarity(dc.text, sc.text)
                if sim > best_sim:
                    best_sim = sim
                    best_match = sc

            if best_match and best_sim >= self._threshold:
                match = _make_match(dc, best_match, best_sim)
                matched.append(match)
                used_standard_ids.add(best_match.id)
                used_draft_ids.add(dc.id)

        # Collect unmatched
        unmatched_draft = [
            UnmatchedClause(
                clause_id=c.id,
                clause_text=c.text,
                clause_type=draft_types.get(c.id, "general"),
                source="draft",
            )
            for c in draft_clauses
            if c.id not in used_draft_ids
        ]

        missing_standard = [
            UnmatchedClause(
                clause_id=c.id,
                clause_text=c.text,
                clause_type=standard_types.get(c.id, "general"),
                source="standard",
            )
            for c in standard_clauses
            if c.id not in used_standard_ids
        ]

        return ComparisonResult(
            matched_clauses=matched,
            unmatched_draft=unmatched_draft,
            missing_standard=missing_standard,
        )


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity using SequenceMatcher (0.0 to 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _make_match(draft: Clause, standard: Clause, similarity: float) -> ClauseMatch:
    """Create a ClauseMatch with risk assessment based on similarity."""
    if similarity >= 0.8:
        risk = "low"
        summary = "Minor deviations from standard"
    elif similarity >= 0.5:
        risk = "medium"
        summary = "Significant deviations from standard clause"
    else:
        risk = "high"
        summary = "Major deviations from standard — requires careful review"

    return ClauseMatch(
        draft_clause_id=draft.id,
        standard_clause_id=standard.id,
        draft_text=draft.text,
        standard_text=standard.text,
        similarity=similarity,
        deviation_summary=summary,
        risk_level=risk,
    )
