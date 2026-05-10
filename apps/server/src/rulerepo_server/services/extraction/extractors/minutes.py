"""Minutes extractor — extracts decisions and action items from meeting minutes.

Only decisions and action items become rule candidates; discussion text is ignored.
See CLAUDE.md §14.11.
"""

from __future__ import annotations

import re

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)

_DECISION_PATTERNS = [
    re.compile(r"(?:決定|決議|合意|承認)[:\uff1a]\s*(.+)", re.MULTILINE),
    re.compile(r"(?:Decided|Agreed|Approved|Resolved)[:\uff1a]\s*(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"【決定事項】\s*(.+)", re.MULTILINE),
]

_ACTION_PATTERNS = [
    re.compile(r"(?:アクション|TODO|対応)[:\uff1a]\s*(.+)", re.MULTILINE),
    re.compile(r"(?:Action item|TODO|Follow-up)[:\uff1a]\s*(.+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"【アクション】\s*(.+)", re.MULTILINE),
]


class MinutesExtractor:
    """Extracts decisions and action items from meeting minutes."""

    source_types = ["minutes"]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from meeting minutes.

        Args:
            source: The minutes document.

        Returns:
            List of CandidateRule from decisions and action items only.
        """
        content = source.content or ""
        if not content and source.path.exists():
            content = source.path.read_text(encoding="utf-8", errors="replace")

        logger.info("minutes_extraction_started", path=str(source.path))

        candidates: list[CandidateRule] = []

        # Extract decisions
        for pattern in _DECISION_PATTERNS:
            for match in pattern.finditer(content):
                decision = match.group(1).strip()
                if len(decision) > 10:
                    candidates.append(
                        CandidateRule(
                            statement=decision[:500],
                            modality="MUST",
                            severity="MEDIUM",
                            source_refs={"document": str(source.path), "type": "decision"},
                            department=source.metadata.get("department", "public"),
                            tags=["minutes", "decision"],
                            applicable_subject_kinds=["event", "document"],
                            confidence=0.6,
                        )
                    )

        # Extract action items
        for pattern in _ACTION_PATTERNS:
            for match in pattern.finditer(content):
                action = match.group(1).strip()
                if len(action) > 10:
                    candidates.append(
                        CandidateRule(
                            statement=action[:500],
                            modality="SHOULD",
                            severity="LOW",
                            source_refs={"document": str(source.path), "type": "action_item"},
                            department=source.metadata.get("department", "public"),
                            tags=["minutes", "action_item"],
                            applicable_subject_kinds=["event"],
                            confidence=0.4,
                        )
                    )

        logger.info("minutes_extraction_complete", candidates=len(candidates))
        return candidates
