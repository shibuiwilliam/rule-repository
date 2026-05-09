"""Clause normalizer — resolves cross-references in legal documents.

Handles patterns like "the preceding article", "Article 5, paragraph 2",
"Section 3.2(a)", and similar legal cross-references.

See CLAUDE.md §14.3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ResolvedReference:
    """A resolved cross-reference in a clause."""

    original_text: str
    resolved_text: str
    target_section: str
    confidence: float = 1.0


# Patterns for common legal cross-references
_ARTICLE_REF = re.compile(r"(?:Article|条)\s+(\d+)(?:\s*,\s*(?:paragraph|項)\s+(\d+))?", re.IGNORECASE)
_SECTION_REF = re.compile(r"Section\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)", re.IGNORECASE)
_PRECEDING_REF = re.compile(
    r"(?:the\s+)?(?:preceding|foregoing|above)\s+(?:article|section|clause|paragraph)",
    re.IGNORECASE,
)
_THIS_REF = re.compile(r"(?:this|the\s+present)\s+(?:article|section|clause|agreement)", re.IGNORECASE)


def normalize_references(
    clause_text: str,
    document_sections: dict[str, str] | None = None,
    current_position: int = 0,
) -> tuple[str, list[ResolvedReference]]:
    """Resolve cross-references in a clause to their target text.

    Args:
        clause_text: The clause text with potential cross-references.
        document_sections: Map of section identifiers to their text.
        current_position: Position of this clause in the document.

    Returns:
        Tuple of (normalized text, list of resolved references).
    """
    resolved: list[ResolvedReference] = []
    sections = document_sections or {}

    # Resolve "the preceding article/section"
    for match in _PRECEDING_REF.finditer(clause_text):
        target = str(current_position - 1) if current_position > 0 else "unknown"
        target_text = sections.get(target, f"[Section {target}]")
        resolved.append(
            ResolvedReference(
                original_text=match.group(),
                resolved_text=target_text,
                target_section=target,
                confidence=0.8 if target in sections else 0.3,
            )
        )

    # Resolve Article N references
    for match in _ARTICLE_REF.finditer(clause_text):
        article = match.group(1)
        paragraph = match.group(2)
        target = f"{article}.{paragraph}" if paragraph else article
        target_text = sections.get(target, f"[Article {target}]")
        resolved.append(
            ResolvedReference(
                original_text=match.group(),
                resolved_text=target_text,
                target_section=target,
                confidence=0.9 if target in sections else 0.5,
            )
        )

    # Resolve Section N.N references
    for match in _SECTION_REF.finditer(clause_text):
        target = match.group(1)
        target_text = sections.get(target, f"[Section {target}]")
        resolved.append(
            ResolvedReference(
                original_text=match.group(),
                resolved_text=target_text,
                target_section=target,
                confidence=0.9 if target in sections else 0.5,
            )
        )

    return clause_text, resolved
