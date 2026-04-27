"""Pattern detector — deduplicates and scores raw patterns.

Groups similar patterns by prefix similarity, keeps the highest-confidence
variant in each group, and applies a boost based on the number of sources
that produced similar patterns.
"""

from __future__ import annotations

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import RawPattern

logger = get_logger(__name__)

# Number of leading characters to compare for similarity grouping
_PREFIX_LENGTH = 50

# Maximum final confidence score
_MAX_CONFIDENCE = 0.99

# Boost factor per additional source that produced a similar pattern
_SOURCE_BOOST = 0.1


def deduplicate_and_score(patterns: list[RawPattern]) -> list[RawPattern]:
    """Deduplicate patterns by prefix similarity and boost confidence.

    Groups patterns by their lowercased first N characters. Within each
    group, keeps the highest-confidence variant and boosts its score
    based on the number of contributing sources.

    Args:
        patterns: Raw patterns from all analyzers.

    Returns:
        Deduplicated and re-scored patterns sorted by confidence descending.
    """
    if not patterns:
        return []

    # Group by lowercased prefix
    groups: dict[str, list[RawPattern]] = {}
    for pattern in patterns:
        key = pattern.statement[:_PREFIX_LENGTH].lower().strip()
        if key not in groups:
            groups[key] = []
        groups[key].append(pattern)

    result: list[RawPattern] = []
    for key, group in groups.items():
        # Keep the variant with the highest base confidence
        best = max(group, key=lambda p: p.confidence)

        # Count unique sources that contributed to this group
        source_count = len({p.source_type for p in group})

        # Apply confidence boost: base * (1 + 0.1 * source_count), capped at 0.99
        boosted_confidence = min(
            best.confidence * (1 + _SOURCE_BOOST * source_count),
            _MAX_CONFIDENCE,
        )

        result.append(
            RawPattern(
                statement=best.statement,
                modality=best.modality,
                severity=best.severity,
                scope=best.scope,
                tags=best.tags,
                source_type=best.source_type,
                source_evidence=best.source_evidence,
                confidence=boosted_confidence,
            )
        )

    # Sort by confidence descending
    result.sort(key=lambda p: p.confidence, reverse=True)

    logger.info(
        "pattern_dedup_complete",
        input_count=len(patterns),
        output_count=len(result),
    )
    return result
