"""Analyzer for CLAUDE.md and AGENTS.md instruction files.

Extracts candidate rules from markdown bullet points, detecting deontic
modality keywords (MUST, SHOULD, MAY, etc.) and using headings as scope hints.
"""

from __future__ import annotations

import re

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import (
    DiscoveryContext,
    RawPattern,
    SourceAnalyzer,
)

logger = get_logger(__name__)

# Patterns that match CLAUDE*.md or AGENTS*.md (case-insensitive)
_FILE_PATTERN = re.compile(r"(CLAUDE|AGENTS).*\.md$", re.IGNORECASE)

# Modality detection patterns — order matters (longer matches first)
_MODALITY_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\bmust\s+not\b", re.IGNORECASE), "MUST_NOT", 0.9),
    (re.compile(r"\bnever\b", re.IGNORECASE), "MUST_NOT", 0.85),
    (re.compile(r"\bdo\s+not\b", re.IGNORECASE), "MUST_NOT", 0.85),
    (re.compile(r"\bmust\b", re.IGNORECASE), "MUST", 0.9),
    (re.compile(r"\brequired\b", re.IGNORECASE), "MUST", 0.85),
    (re.compile(r"\bshould\s+not\b", re.IGNORECASE), "SHOULD", 0.8),
    (re.compile(r"\bshould\b", re.IGNORECASE), "SHOULD", 0.8),
    (re.compile(r"\balways\b", re.IGNORECASE), "SHOULD", 0.8),
    (re.compile(r"\bprefer\b", re.IGNORECASE), "SHOULD", 0.75),
    (re.compile(r"\bmay\b", re.IGNORECASE), "MAY", 0.7),
    (re.compile(r"\bcan\b", re.IGNORECASE), "MAY", 0.7),
]

# Heading pattern to extract scope hints
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Bullet point pattern (-, *, or numbered)
_BULLET_PATTERN = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
_NUMBERED_PATTERN = re.compile(r"^\s*\d+\.\s+(.+)$", re.MULTILINE)


class ClaudeMdAnalyzer(SourceAnalyzer):
    """Extracts candidate rules from CLAUDE.md and AGENTS.md files.

    Parses markdown structure: headings become scope hints, bullet points
    and numbered items are candidate rule statements. Deontic keywords
    determine modality and influence confidence scoring.
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze CLAUDE.md / AGENTS.md files for candidate rules.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns extracted from matching files.
        """
        patterns: list[RawPattern] = []

        matching_files = {
            path: content
            for path, content in context.file_contents.items()
            if _FILE_PATTERN.search(path.split("/")[-1])
        }

        if not matching_files:
            logger.debug("claude_md_analyzer_no_files")
            return patterns

        for path, content in matching_files.items():
            logger.info("claude_md_analyzing", path=path)
            file_patterns = self._parse_file(path, content)
            patterns.extend(file_patterns)

        logger.info("claude_md_analysis_complete", pattern_count=len(patterns))
        return patterns

    def _parse_file(self, path: str, content: str) -> list[RawPattern]:
        """Parse a single markdown file into raw patterns.

        Args:
            path: File path for provenance.
            content: Full file content.

        Returns:
            List of patterns found in the file.
        """
        patterns: list[RawPattern] = []
        current_scope: list[str] = []

        lines = content.split("\n")
        for line in lines:
            # Update scope context from headings
            heading_match = _HEADING_PATTERN.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                # Reset scope at this level and above
                current_scope = current_scope[: max(0, level - 1)]
                current_scope.append(heading_text.lower())
                continue

            # Extract bullet or numbered items
            bullet_match = _BULLET_PATTERN.match(line) or _NUMBERED_PATTERN.match(line)
            if not bullet_match:
                continue

            text = bullet_match.group(1).strip()
            if len(text) < 15:
                # Too short to be a meaningful rule
                continue

            modality, confidence = self._detect_modality(text)
            if modality is None:
                # No deontic keyword found — skip or use low confidence
                confidence = 0.4
                modality = "INFO"

            patterns.append(
                RawPattern(
                    statement=text,
                    modality=modality,
                    severity=self._infer_severity(modality),
                    scope=list(current_scope),
                    tags=["claude_md"],
                    source_type="claude_md",
                    source_evidence=text,
                    confidence=confidence,
                )
            )

        return patterns

    def _detect_modality(self, text: str) -> tuple[str | None, float]:
        """Detect deontic modality from keywords in text.

        Args:
            text: The candidate rule text.

        Returns:
            Tuple of (modality, confidence) or (None, 0.0) if no keyword found.
        """
        for pattern, modality, confidence in _MODALITY_PATTERNS:
            if pattern.search(text):
                return modality, confidence
        return None, 0.0

    def _infer_severity(self, modality: str | None) -> str:
        """Infer severity from modality as a reasonable default.

        Args:
            modality: The detected modality.

        Returns:
            A severity string.
        """
        if modality in ("MUST", "MUST_NOT"):
            return "HIGH"
        if modality == "SHOULD":
            return "MEDIUM"
        return "LOW"
