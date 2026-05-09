"""Document region subject — the unit of evaluation for the document surface.

See CLAUDE.md §14.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DocumentRegion:
    """Subject representing a document or document region for evaluation.

    Attributes:
        content: The document text or section content.
        document_type: Classification (e.g., "policy", "disclosure",
            "report", "marketing_copy", "handbook").
        title: Document title.
        section: Section identifier or heading.
        author: Document author.
        version: Document version string.
        classification: Sensitivity classification (e.g., "public",
            "internal", "confidential").
        facts: Additional structured facts.
        description: Narrative description.
        timestamp: When the document was submitted for evaluation.
        locale: Language of the document (default "en").
    """

    content: str = ""
    document_type: str = "general"
    title: str = ""
    section: str = ""
    author: str = ""
    version: str = ""
    classification: str = "internal"
    facts: dict[str, object] = field(default_factory=dict)
    description: str = ""
    timestamp: datetime | None = None
    locale: str = "en"
