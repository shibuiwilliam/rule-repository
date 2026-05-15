"""Plain text structure parser.

Splits plain text into paragraph-level sections.
"""

from __future__ import annotations

import re

from rulerepo_server.services.extraction.structural.pdf_structure import (
    DocumentSection,
    StructuralExtractionResult,
)


def extract_text_structure(content: str) -> StructuralExtractionResult:
    """Parse plain text into sections based on blank-line-separated paragraphs."""
    paragraphs = re.split(r"\n\s*\n", content.strip())
    sections = []

    for i, para in enumerate(paragraphs, 1):
        text = para.strip()
        if text:
            sections.append(
                DocumentSection(
                    section_id=f"para_{i}",
                    title=f"Paragraph {i}",
                    level=0,
                    content=text,
                )
            )

    return StructuralExtractionResult(
        sections=sections,
        document_type="text",
    )
