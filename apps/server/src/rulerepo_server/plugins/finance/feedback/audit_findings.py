"""Audit findings feedback source for finance domain.

Tracks denied transactions, overridden approvals, and other audit events
to detect patterns that suggest rule tightening or new rule creation.

See: CLAUDE.md SS14.9
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default configuration
DEFAULT_VIOLATION_THRESHOLD = 5
DEFAULT_VIOLATION_WINDOW_DAYS = 60
DEFAULT_SPLIT_PATTERN_THRESHOLD = 3
DEFAULT_VENDOR_CONCENTRATION_THRESHOLD = 0.7


@dataclass
class AuditFindingsConfig:
    """Configuration for audit findings analysis.

    Attributes:
        violation_threshold: Number of violations before suggesting tightening.
        violation_window_days: Days to look back for pattern detection.
        split_pattern_threshold: Min occurrences to flag split pattern.
        vendor_concentration_threshold: Ratio threshold for single-vendor
            concentration (0.0 to 1.0).
    """

    violation_threshold: int = DEFAULT_VIOLATION_THRESHOLD
    violation_window_days: int = DEFAULT_VIOLATION_WINDOW_DAYS
    split_pattern_threshold: int = DEFAULT_SPLIT_PATTERN_THRESHOLD
    vendor_concentration_threshold: float = DEFAULT_VENDOR_CONCENTRATION_THRESHOLD


@dataclass
class FindingRecord:
    """Internal record of an audit finding event.

    Attributes:
        event_type: Type of audit event (denied, overridden, flagged).
        category: Expense category involved.
        vendor: Vendor/payee name.
        amount: Transaction amount.
        employee_id: Employee who submitted.
        timestamp: When the event occurred.
        reason: Reason for the finding.
    """

    event_type: str
    category: str
    vendor: str
    amount: int | float
    employee_id: str
    timestamp: datetime
    reason: str = ""


class AuditFindingsCapture:
    """Feedback source tracking audit findings for pattern detection.

    Monitors denied transactions and overridden approvals. When patterns
    emerge (repeated violations by category/vendor, split transaction
    patterns, budget overruns), generates suggestions for rule tightening
    or new rule creation.

    Args:
        config: Configuration for thresholds and windows.
    """

    def __init__(self, config: AuditFindingsConfig | None = None) -> None:
        self._config = config or AuditFindingsConfig()
        self._findings: list[FindingRecord] = []

    @property
    def name(self) -> str:
        """Unique name of this feedback source."""
        return "audit_findings_capture"

    @property
    def domain(self) -> str:
        """Domain identifier."""
        return "finance"

    async def capture(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Capture an audit event and return any triggered suggestions.

        Accepts events of types: transaction_denied, approval_overridden,
        split_detected, budget_exceeded. Stores the finding and analyzes
        accumulated data for patterns.

        Args:
            event: Raw audit event dict with fields: event_type, category,
                vendor, amount, employee_id, timestamp, reason.

        Returns:
            List of suggestion dicts if patterns are detected, empty
            list otherwise. Each suggestion contains: type, category/vendor,
            suggestion text, and evidence_count.
        """
        record = self._parse_event(event)
        if record is None:
            logger.warning("audit_event_unparseable", event_keys=list(event.keys()))
            return []

        self._findings.append(record)
        self._prune_old_findings()

        logger.info(
            "audit_finding_captured",
            event_type=record.event_type,
            category=record.category,
            vendor=record.vendor,
            total_findings=len(self._findings),
        )

        suggestions: list[dict[str, Any]] = []

        # Analyze patterns
        suggestions.extend(self._detect_category_violations(record.category))
        suggestions.extend(self._detect_vendor_violations(record.vendor))
        suggestions.extend(self._detect_split_patterns())
        suggestions.extend(self._detect_budget_overruns())
        suggestions.extend(self._detect_vendor_concentration())

        if suggestions:
            logger.info(
                "audit_suggestions_generated",
                suggestion_count=len(suggestions),
                types=[s["type"] for s in suggestions],
            )

        return suggestions

    def _parse_event(self, event: dict[str, Any]) -> FindingRecord | None:
        """Parse a raw event dict into a FindingRecord.

        Args:
            event: Raw event data.

        Returns:
            FindingRecord or None if event is invalid.
        """
        event_type = event.get("event_type", "")
        valid_types = {
            "transaction_denied",
            "approval_overridden",
            "split_detected",
            "budget_exceeded",
        }
        if event_type not in valid_types:
            return None

        timestamp_raw = event.get("timestamp", "")
        timestamp = self._parse_timestamp(timestamp_raw)
        if timestamp is None:
            timestamp = datetime.now()

        return FindingRecord(
            event_type=event_type,
            category=str(event.get("category", "")).lower(),
            vendor=str(event.get("vendor", event.get("payee", ""))).lower().strip(),
            amount=event.get("amount", 0),
            employee_id=str(event.get("employee_id", "unknown")),
            timestamp=timestamp,
            reason=str(event.get("reason", "")),
        )

    def _prune_old_findings(self) -> None:
        """Remove findings outside the analysis window."""
        cutoff = datetime.now() - timedelta(days=self._config.violation_window_days)
        self._findings = [f for f in self._findings if f.timestamp >= cutoff]

    def _detect_category_violations(self, category: str) -> list[dict[str, Any]]:
        """Detect repeated violations in a specific category.

        Args:
            category: Category to check.

        Returns:
            List of suggestions if threshold exceeded.
        """
        if not category:
            return []

        violations = [f for f in self._findings if f.category == category]
        if len(violations) >= self._config.violation_threshold:
            return [
                {
                    "type": "rule_tightening",
                    "category": category,
                    "suggestion": (
                        f"Category '{category}' has {len(violations)} violations "
                        f"in the last {self._config.violation_window_days} days. "
                        f"Consider tightening limits or adding pre-approval requirements."
                    ),
                    "evidence_count": len(violations),
                    "pattern": "repeated_category_violation",
                }
            ]
        return []

    def _detect_vendor_violations(self, vendor: str) -> list[dict[str, Any]]:
        """Detect repeated violations with a specific vendor.

        Args:
            vendor: Vendor name to check.

        Returns:
            List of suggestions if threshold exceeded.
        """
        if not vendor:
            return []

        violations = [f for f in self._findings if f.vendor == vendor]
        if len(violations) >= self._config.violation_threshold:
            total_amount = sum(v.amount for v in violations)
            return [
                {
                    "type": "vendor_restriction",
                    "vendor": vendor,
                    "suggestion": (
                        f"Vendor '{vendor}' has {len(violations)} violations "
                        f"totaling {total_amount} in the last "
                        f"{self._config.violation_window_days} days. "
                        f"Consider adding vendor to restricted list or requiring "
                        f"additional documentation."
                    ),
                    "evidence_count": len(violations),
                    "total_amount": total_amount,
                    "pattern": "repeated_vendor_violation",
                }
            ]
        return []

    def _detect_split_patterns(self) -> list[dict[str, Any]]:
        """Detect recurring split transaction patterns.

        Groups findings by employee+vendor and flags systematic splitting.

        Returns:
            List of suggestions if split patterns detected.
        """
        split_findings = [f for f in self._findings if f.event_type == "split_detected"]

        # Group by employee
        by_employee: dict[str, list[FindingRecord]] = defaultdict(list)
        for finding in split_findings:
            by_employee[finding.employee_id].append(finding)

        suggestions: list[dict[str, Any]] = []
        for employee_id, findings in by_employee.items():
            if len(findings) >= self._config.split_pattern_threshold:
                vendors = set(f.vendor for f in findings if f.vendor)
                suggestions.append(
                    {
                        "type": "rule_tightening",
                        "category": "split_transactions",
                        "suggestion": (
                            f"Employee '{employee_id}' has {len(findings)} split "
                            f"transaction flags involving vendors: "
                            f"{', '.join(vendors) if vendors else 'various'}. "
                            f"Consider lowering split detection threshold or "
                            f"requiring consolidated submissions."
                        ),
                        "evidence_count": len(findings),
                        "employee_id": employee_id,
                        "pattern": "recurring_split_transactions",
                    }
                )

        return suggestions

    def _detect_budget_overruns(self) -> list[dict[str, Any]]:
        """Detect categories that are consistently over budget.

        Returns:
            List of suggestions for consistently over-budget categories.
        """
        budget_findings = [f for f in self._findings if f.event_type == "budget_exceeded"]

        by_category: dict[str, list[FindingRecord]] = defaultdict(list)
        for finding in budget_findings:
            if finding.category:
                by_category[finding.category].append(finding)

        suggestions: list[dict[str, Any]] = []
        for category, findings in by_category.items():
            if len(findings) >= self._config.violation_threshold:
                total_over = sum(f.amount for f in findings)
                suggestions.append(
                    {
                        "type": "budget_review",
                        "category": category,
                        "suggestion": (
                            f"Category '{category}' has exceeded budget "
                            f"{len(findings)} times in the last "
                            f"{self._config.violation_window_days} days "
                            f"(total overage: {total_over}). "
                            f"Consider revising the budget allocation or "
                            f"splitting into sub-categories with individual limits."
                        ),
                        "evidence_count": len(findings),
                        "total_overage": total_over,
                        "pattern": "consistent_budget_overrun",
                    }
                )

        return suggestions

    def _detect_vendor_concentration(self) -> list[dict[str, Any]]:
        """Detect single-vendor concentration in spending.

        Flags when one vendor accounts for a disproportionate share
        of total transaction volume.

        Returns:
            List of suggestions if concentration detected.
        """
        if len(self._findings) < self._config.violation_threshold:
            return []

        vendor_counts: dict[str, int] = defaultdict(int)
        for finding in self._findings:
            if finding.vendor:
                vendor_counts[finding.vendor] += 1

        total = len(self._findings)
        suggestions: list[dict[str, Any]] = []

        for vendor, count in vendor_counts.items():
            ratio = count / total
            if ratio >= self._config.vendor_concentration_threshold:
                suggestions.append(
                    {
                        "type": "vendor_concentration",
                        "vendor": vendor,
                        "suggestion": (
                            f"Vendor '{vendor}' accounts for {ratio:.0%} of "
                            f"audit findings ({count}/{total}). "
                            f"Consider requiring competitive quotes or "
                            f"diversifying approved vendor list."
                        ),
                        "evidence_count": count,
                        "concentration_ratio": ratio,
                        "pattern": "single_vendor_concentration",
                    }
                )

        return suggestions

    @staticmethod
    def _parse_timestamp(timestamp_raw: Any) -> datetime | None:
        """Parse a timestamp value into a datetime.

        Args:
            timestamp_raw: String or datetime timestamp.

        Returns:
            Parsed datetime or None.
        """
        if isinstance(timestamp_raw, datetime):
            return timestamp_raw

        if not isinstance(timestamp_raw, str) or not timestamp_raw:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_raw[: len(fmt) + 5], fmt)
            except (ValueError, IndexError):
                continue
        return None
