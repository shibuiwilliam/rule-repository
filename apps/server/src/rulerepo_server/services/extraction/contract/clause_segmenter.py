"""Clause segmenter — breaks contract text into article/section/paragraph units.

Each clause gets an identifier (e.g., "Article 3, Section 2(b)") and a
hierarchical position within the document.

Supports both Western-style numbering ("Section 3(b)") and Japanese-style
references ("第3条第2項").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Clause:
    """A single clause extracted from a contract document.

    Attributes:
        id: Stable identifier within the document (e.g., "art3.sec2.para_b").
        heading: The clause heading or number (e.g., "Article 3").
        text: The full clause text.
        level: Nesting depth (0 = article, 1 = section, 2 = paragraph).
        parent_id: ID of the parent clause, if any.
    """

    id: str
    heading: str
    text: str
    level: int = 0
    parent_id: str | None = None


@dataclass
class SegmentedDocument:
    """A contract broken into hierarchical clauses."""

    title: str = ""
    clauses: list[Clause] = field(default_factory=list)
    preamble: str = ""

    @property
    def clause_count(self) -> int:
        return len(self.clauses)


# -- Regex patterns for common clause structures --

_ARTICLE_WESTERN = re.compile(
    r"^(?:Article|ARTICLE|Section|SECTION|Clause|CLAUSE)\s+(\d+)[\.\:]?\s*(.*)",
    re.MULTILINE,
)
_ARTICLE_JAPANESE = re.compile(
    r"^第(\d+)条\s*(.*)",
    re.MULTILINE,
)
_SUBSECTION = re.compile(
    r"^\s*(?:(\d+)\.|(\([a-z]\))|(\([ivxlc]+\)))\s+(.*)",
    re.MULTILINE,
)


class ClauseSegmenter:
    """Convenience wrapper around :func:`segment_contract`."""

    def segment(self, text: str, *, title: str = "") -> SegmentedDocument:
        """Segment a contract into hierarchical clauses."""
        return segment_contract(text, title=title)


def segment_contract(text: str, *, title: str = "") -> SegmentedDocument:
    """Segment a contract into hierarchical clauses.

    Uses pattern matching on common article/section/paragraph numbering
    conventions. For complex or ambiguous documents, the LLM-based
    segmenter in the extraction pipeline should be used instead.

    Args:
        text: The full contract text.
        title: Optional document title.

    Returns:
        A SegmentedDocument with extracted clauses.
    """
    doc = SegmentedDocument(title=title)
    lines = text.split("\n")

    current_article_id = ""
    current_article_num = 0
    buffer: list[str] = []
    preamble_done = False

    for line in lines:
        # Try Western article pattern
        m = _ARTICLE_WESTERN.match(line.strip())
        if not m:
            m = _ARTICLE_JAPANESE.match(line.strip())

        if m:
            # Flush previous buffer
            if current_article_id and buffer:
                doc.clauses.append(
                    Clause(
                        id=current_article_id,
                        heading=f"Article {current_article_num}",
                        text="\n".join(buffer).strip(),
                        level=0,
                    )
                )
                buffer = []
            elif not preamble_done and buffer:
                doc.preamble = "\n".join(buffer).strip()
                buffer = []
                preamble_done = True

            current_article_num = int(m.group(1))
            current_article_id = f"art{current_article_num}"
            heading_text = m.group(2).strip() if m.group(2) else ""
            if heading_text:
                buffer.append(heading_text)
            preamble_done = True
        else:
            buffer.append(line)

    # Flush last article
    if current_article_id and buffer:
        doc.clauses.append(
            Clause(
                id=current_article_id,
                heading=f"Article {current_article_num}",
                text="\n".join(buffer).strip(),
                level=0,
            )
        )
    elif not preamble_done and buffer:
        doc.preamble = "\n".join(buffer).strip()

    return doc
