"""Base classes for source analyzers in the rule discovery pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawPattern:
    """A candidate rule pattern discovered from a source file.

    Attributes:
        statement: The rule statement text.
        modality: Deontic modality (MUST, SHOULD, etc.) or None if unknown.
        severity: Severity level or None if unknown.
        scope: List of scope tags (e.g., ["python", "backend"]).
        tags: Freeform tags for categorization.
        source_type: Identifier for the analyzer that produced this pattern.
        source_evidence: The raw text or config snippet that supports this pattern.
        confidence: Confidence score in [0, 1].
    """

    statement: str
    modality: str | None = None
    severity: str | None = None
    scope: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_type: str = ""
    source_evidence: str = ""
    confidence: float = 0.5


@dataclass
class DiscoveryContext:
    """Input context provided to source analyzers.

    Attributes:
        file_paths: List of file paths available for analysis.
        file_contents: Mapping of file path to file content text.
        repository: Optional repository name or URL.
    """

    file_paths: list[str] = field(default_factory=list)
    file_contents: dict[str, str] = field(default_factory=dict)
    repository: str | None = None


class SourceAnalyzer(ABC):
    """Abstract base class for source analyzers.

    Each analyzer inspects a specific type of source file (CLAUDE.md, linter
    configs, code patterns, etc.) and returns discovered rule patterns.
    """

    @abstractmethod
    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze the provided context and return discovered patterns.

        Args:
            context: The discovery context with file paths and contents.

        Returns:
            A list of raw patterns found in the source files.
        """
        ...
