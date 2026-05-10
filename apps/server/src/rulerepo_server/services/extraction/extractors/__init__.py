"""Domain-specific extractors for the rule extraction pipeline.

Each extractor implements the Extractor protocol and handles a specific
document type. See CLAUDE.md §14.11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class CandidateRule:
    """A candidate rule extracted from a source document."""

    statement: str
    modality: str = "SHOULD"
    severity: str = "MEDIUM"
    scope: list[str] = field(default_factory=list)
    source_refs: dict[str, Any] = field(default_factory=dict)
    department: str = "public"
    tags: list[str] = field(default_factory=list)
    rationale: str = ""
    context: str = ""
    applicable_subject_kinds: list[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class SourceFile:
    """A source file to extract rules from."""

    path: Path
    source_type: str
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Extractor(Protocol):
    """Protocol that every source-type extractor must implement."""

    source_types: list[str]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from the source file."""
        ...
