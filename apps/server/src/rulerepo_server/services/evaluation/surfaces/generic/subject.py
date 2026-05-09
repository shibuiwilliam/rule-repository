"""Generic subject — fallback for unclassified evaluation targets.

Used when the subject does not fit any specific surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class GenericSubject:
    """Fallback subject for free-form evaluation.

    Attributes:
        content: Free-form content to evaluate.
        description: Narrative description of what is being evaluated.
        facts: Structured facts that any rule may consult.
        timestamp: When the subject was submitted.
        locale: Language of the content (default "en").
    """

    content: str = ""
    description: str = ""
    facts: dict[str, object] = field(default_factory=dict)
    timestamp: datetime | None = None
    locale: str = "en"
