"""Reference resolver — resolves cross-references within and between contracts.

Handles patterns like "Section 3(b)", "前項", "別紙X", "as defined in Article 2",
and maps them to clause IDs produced by the clause segmenter.

See: IMPROVEMENT.md §3.1, PROJECT.md §5.3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rulerepo_server.services.extraction.contract.clause_segmenter import (
    SegmentedDocument,
)

# ---------------------------------------------------------------------------
# Reference patterns
# ---------------------------------------------------------------------------

_REF_WESTERN = re.compile(
    r"(?:Article|Section|Clause)\s+(\d+)(?:\s*\(([a-z])\))?",
    re.IGNORECASE,
)
_REF_JAPANESE_ARTICLE = re.compile(r"第(\d+)条")
_REF_JAPANESE_PARAGRAPH = re.compile(r"第(\d+)項")
_REF_PRECEDING = re.compile(r"前項|前条|the preceding (?:section|article|clause)", re.IGNORECASE)
_REF_APPENDIX = re.compile(r"(?:別紙|Appendix|Exhibit|Schedule)\s*([A-Z0-9])?", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedReference:
    """A cross-reference found in clause text, resolved to a target clause.

    Attributes:
        source_clause_id: The clause containing the reference.
        match_text: The matched reference text (e.g., "Section 3(b)").
        target_clause_id: The resolved target clause ID, or None if unresolved.
        reference_type: Type of reference (internal, preceding, appendix).
    """

    source_clause_id: str
    match_text: str
    target_clause_id: str | None
    reference_type: str = "internal"


@dataclass
class ReferenceMap:
    """All resolved references within a document."""

    references: list[ResolvedReference] = field(default_factory=list)

    @property
    def unresolved_count(self) -> int:
        return sum(1 for r in self.references if r.target_clause_id is None)


def resolve_references(doc: SegmentedDocument) -> ReferenceMap:
    """Find and resolve cross-references across all clauses in a document.

    Args:
        doc: A segmented document with clauses.

    Returns:
        A ReferenceMap containing all found references.
    """
    # Build a number-to-id lookup
    num_to_id: dict[int, str] = {}
    for clause in doc.clauses:
        m = re.search(r"(\d+)", clause.id)
        if m:
            num_to_id[int(m.group(1))] = clause.id

    ref_map = ReferenceMap()

    for i, clause in enumerate(doc.clauses):
        text = clause.text

        # Western-style references
        for m in _REF_WESTERN.finditer(text):
            article_num = int(m.group(1))
            target_id = num_to_id.get(article_num)
            ref_map.references.append(
                ResolvedReference(
                    source_clause_id=clause.id,
                    match_text=m.group(0),
                    target_clause_id=target_id,
                    reference_type="internal",
                )
            )

        # Japanese-style article references
        for m in _REF_JAPANESE_ARTICLE.finditer(text):
            article_num = int(m.group(1))
            target_id = num_to_id.get(article_num)
            ref_map.references.append(
                ResolvedReference(
                    source_clause_id=clause.id,
                    match_text=m.group(0),
                    target_clause_id=target_id,
                    reference_type="internal",
                )
            )

        # Preceding section/article references
        for m in _REF_PRECEDING.finditer(text):
            prev_id = doc.clauses[i - 1].id if i > 0 else None
            ref_map.references.append(
                ResolvedReference(
                    source_clause_id=clause.id,
                    match_text=m.group(0),
                    target_clause_id=prev_id,
                    reference_type="preceding",
                )
            )

        # Appendix references
        for m in _REF_APPENDIX.finditer(text):
            ref_map.references.append(
                ResolvedReference(
                    source_clause_id=clause.id,
                    match_text=m.group(0),
                    target_clause_id=None,
                    reference_type="appendix",
                )
            )

    return ref_map
