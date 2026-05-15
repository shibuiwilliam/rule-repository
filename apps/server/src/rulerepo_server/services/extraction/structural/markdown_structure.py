"""Markdown structure parser.

Parses markdown documents into hierarchical sections using heading levels.
No Gemini API needed — pure text parsing.
"""

from __future__ import annotations

import re

from rulerepo_server.services.extraction.structural.pdf_structure import (
    DocumentSection,
    StructuralExtractionResult,
)


def extract_markdown_structure(content: str) -> StructuralExtractionResult:
    """Parse a markdown document into hierarchical sections."""
    sections: list[DocumentSection] = []
    current_section: DocumentSection | None = None
    section_counter = 0
    content_lines: list[str] = []

    for line in content.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # Save previous section
            if current_section is not None:
                current_section.content = "\n".join(content_lines).strip()
                sections.append(current_section)

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            section_counter += 1
            current_section = DocumentSection(
                section_id=f"sec_{section_counter}",
                title=title,
                level=level,
                content="",
            )
            content_lines = []
        else:
            content_lines.append(line)

    # Save last section
    if current_section is not None:
        current_section.content = "\n".join(content_lines).strip()
        sections.append(current_section)
    elif any(line.strip() for line in content_lines):
        # No headings found — treat entire content as one section
        sections.append(
            DocumentSection(
                section_id="sec_1",
                title="(untitled)",
                level=0,
                content="\n".join(content_lines).strip(),
            )
        )

    return StructuralExtractionResult(
        sections=sections,
        document_type="markdown",
    )
