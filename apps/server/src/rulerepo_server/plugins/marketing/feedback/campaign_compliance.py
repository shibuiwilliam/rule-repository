"""Campaign compliance feedback source for marketing plugin.

Tracks compliance issues by campaign, content type, and violation
category. Detects recurring patterns and suggests preventive rules
when violations repeat above a configurable threshold.

See: CLAUDE.md SS14.9
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default threshold: number of violations of the same type in the same
# campaign/content-type before a preventive rule is suggested.
_DEFAULT_PATTERN_THRESHOLD = 3


class _ViolationRecord:
    """Internal record of a single compliance violation event."""

    __slots__ = (
        "campaign",
        "check_name",
        "content_type",
        "details",
        "timestamp",
        "violation_category",
    )

    def __init__(
        self,
        campaign: str,
        content_type: str,
        violation_category: str,
        check_name: str,
        timestamp: datetime,
        details: dict[str, Any],
    ) -> None:
        self.campaign = campaign
        self.content_type = content_type
        self.violation_category = violation_category
        self.check_name = check_name
        self.timestamp = timestamp
        self.details = details


class CampaignComplianceCapture:
    """Feedback source that detects recurring compliance patterns.

    Tracks violations across campaigns and content types. When the
    same violation category recurs above a threshold within a campaign
    or content-type grouping, suggests a preventive rule to address
    the root cause.

    Args:
        pattern_threshold: Number of same-type violations before
            a preventive rule suggestion is generated. Defaults to 3.
    """

    def __init__(self, pattern_threshold: int = _DEFAULT_PATTERN_THRESHOLD) -> None:
        self._pattern_threshold = pattern_threshold
        # Key: (campaign, content_type, violation_category)
        self._violation_counts: dict[tuple[str, str, str], list[_ViolationRecord]] = defaultdict(list)
        # Track already-suggested patterns to avoid duplicates
        self._suggested_patterns: set[tuple[str, str, str]] = set()

    @property
    def name(self) -> str:
        return "campaign_compliance_capture"

    @property
    def domain(self) -> str:
        return "marketing"

    async def capture(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Capture a compliance event and detect recurring patterns.

        Args:
            event: A compliance event dict containing:
                - campaign (str): Campaign identifier.
                - content_type (str): Type of content evaluated.
                - violations (list[dict]): List of violation dicts,
                  each with 'check' and 'category' keys.
                - timestamp (str, optional): ISO timestamp.

        Returns:
            List of preventive rule suggestion dicts when patterns
            are detected. Empty list if no pattern threshold is met.
        """
        campaign = event.get("campaign", "unknown")
        content_type = event.get("content_type", "unknown")
        violations = event.get("violations", [])
        timestamp_str = event.get("timestamp")

        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError):
                timestamp = datetime.now(tz=UTC)
        else:
            timestamp = datetime.now(tz=UTC)

        if not violations:
            return []

        logger.debug(
            "campaign_compliance_event_captured",
            campaign=campaign,
            content_type=content_type,
            violation_count=len(violations),
        )

        suggestions: list[dict[str, Any]] = []

        for violation in violations:
            if not isinstance(violation, dict):
                continue

            category: str = str(violation.get("category", violation.get("check", "unknown")))
            check_name: str = str(violation.get("check", "unknown"))

            record = _ViolationRecord(
                campaign=campaign,
                content_type=content_type,
                violation_category=category,
                check_name=check_name,
                timestamp=timestamp,
                details=violation,
            )

            key = (campaign, content_type, category)
            self._violation_counts[key].append(record)

            # Check if threshold is met and not already suggested
            if len(self._violation_counts[key]) >= self._pattern_threshold and key not in self._suggested_patterns:
                self._suggested_patterns.add(key)
                suggestion = self._build_suggestion(key)
                suggestions.append(suggestion)

                logger.info(
                    "campaign_compliance_pattern_detected",
                    campaign=campaign,
                    content_type=content_type,
                    violation_category=category,
                    occurrence_count=len(self._violation_counts[key]),
                )

        return suggestions

    def _build_suggestion(
        self,
        key: tuple[str, str, str],
    ) -> dict[str, Any]:
        """Build a preventive rule suggestion for a detected pattern.

        Args:
            key: Tuple of (campaign, content_type, violation_category).

        Returns:
            Suggestion dict with type, context, and recommendation.
        """
        campaign, content_type, category = key
        records = self._violation_counts[key]
        occurrence_count = len(records)

        # Collect representative details from violations
        sample_details = [r.details for r in records[:3]]

        return {
            "type": "preventive_rule",
            "campaign": campaign,
            "content_type": content_type,
            "violation_pattern": category,
            "occurrence_count": occurrence_count,
            "threshold": self._pattern_threshold,
            "suggestion": (
                f"キャンペーン '{campaign}' のコンテンツタイプ '{content_type}' で "
                f"違反カテゴリ '{category}' が {occurrence_count} 回発生しています。"
                f"予防ルールの作成を推奨します。"
            ),
            "suggestion_en": (
                f"Campaign '{campaign}' with content type '{content_type}' has "
                f"{occurrence_count} occurrences of violation category '{category}'. "
                f"Consider creating a preventive rule."
            ),
            "sample_violations": sample_details,
            "recommended_scope": ["marketing/brand", f"marketing/{content_type}"],
            "recommended_tags": [
                "auto-suggested",
                "preventive",
                f"campaign:{campaign}",
                f"violation:{category}",
            ],
        }

    def get_violation_summary(self) -> dict[str, Any]:
        """Get a summary of all tracked violations.

        Returns:
            Summary dict with counts by campaign, content type, and
            category.
        """
        summary: dict[str, int] = {}
        for key, records in self._violation_counts.items():
            campaign, content_type, category = key
            label = f"{campaign}/{content_type}/{category}"
            summary[label] = len(records)

        return {
            "total_patterns_tracked": len(self._violation_counts),
            "patterns_above_threshold": len(self._suggested_patterns),
            "breakdown": summary,
        }

    def reset(self) -> None:
        """Reset all tracked state.

        Useful for testing or periodic cleanup.
        """
        self._violation_counts.clear()
        self._suggested_patterns.clear()
        logger.info("campaign_compliance_capture_reset")
