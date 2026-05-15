"""Cross-reference resolution for extracted normative sentences.

Resolves references like "the preceding paragraph", "Article 3",
"Section 2.1" to their target sections.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.structural.pdf_structure import (
    DocumentSection,
)

logger = get_logger(__name__)


@dataclass
class ResolvedReference:
    """A resolved cross-reference."""

    source_text: str
    reference_text: str
    target_section_id: str | None
    resolved: bool


def resolve_references(
    text: str,
    sections: list[DocumentSection],
) -> list[ResolvedReference]:
    """Resolve cross-references in text against available sections.

    Handles patterns like:
    - "Section X.Y" / "section X.Y"
    - "Article X" / "article X"
    - Japanese article references ("第X条")

    This is a basic implementation. LLM-assisted resolution
    is available via the extraction pipeline for complex cases.
    """
    references: list[ResolvedReference] = []

    # English section references
    for match in re.finditer(r"(?:Section|§)\s*([\d.]+)", text, re.IGNORECASE):
        ref_text = match.group(0)
        target = _find_section_by_number(match.group(1), sections)
        references.append(
            ResolvedReference(
                source_text=text,
                reference_text=ref_text,
                target_section_id=target.section_id if target else None,
                resolved=target is not None,
            )
        )

    # Japanese article references (第X条)
    for match in re.finditer(r"第(\d+)条", text):
        ref_text = match.group(0)
        target = _find_section_by_title_pattern(f"第{match.group(1)}条", sections)
        references.append(
            ResolvedReference(
                source_text=text,
                reference_text=ref_text,
                target_section_id=target.section_id if target else None,
                resolved=target is not None,
            )
        )

    return references


def _find_section_by_number(
    number: str,
    sections: list[DocumentSection],
) -> DocumentSection | None:
    """Find a section by its number (e.g., '2.1')."""
    for section in sections:
        if number in section.title or section.section_id.endswith(f"_{number}"):
            return section
    return None


def _find_section_by_title_pattern(
    pattern: str,
    sections: list[DocumentSection],
) -> DocumentSection | None:
    """Find a section whose title contains the given pattern."""
    for section in sections:
        if pattern in section.title:
            return section
    return None
