"""Violation pattern capture — tracks recurring HR violations for rule refinement.

Monitors HR evaluation outcomes and identifies recurring violation patterns
by department, employee, and violation type. When a pattern repeats 3+ times
within 30 days, generates rule refinement suggestions.

See: CLAUDE.md SS14.7
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Pattern detection thresholds
_REPEAT_THRESHOLD = 3
_PATTERN_WINDOW_DAYS = 30
_RETENTION_DAYS = 90


@dataclass
class _ViolationEntry:
    """A single recorded violation event."""

    timestamp: datetime
    department: str
    employee_id: str
    violation_type: str
    rule_id: str
    severity: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class _PatternKey:
    """Key for grouping violations into patterns."""

    department: str
    violation_type: str

    def __hash__(self) -> int:
        return hash((self.department, self.violation_type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _PatternKey):
            return NotImplemented
        return self.department == other.department and self.violation_type == other.violation_type


class ViolationPatternCapture:
    """Captures recurring HR violation patterns and suggests rule refinements.

    Maintains an in-memory sliding window of recent violations (last 90 days)
    and detects when a pattern repeats 3+ times within 30 days. Generates
    suggestions for rule tightening or process changes.
    """

    def __init__(self) -> None:
        self._violations: list[_ViolationEntry] = []

    @property
    def name(self) -> str:
        return "violation_patterns"

    @property
    def domain(self) -> str:
        return "hr"

    async def capture(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Process a violation event and return any pattern-based suggestions.

        Args:
            event: Violation event dict with fields: timestamp, department,
                employee_id, violation_type, rule_id, severity, and
                optional details.

        Returns:
            List of suggestion dicts when patterns are detected. Each
            suggestion contains: type, suggestion, evidence_count,
            pattern_description, department, violation_type, rule_id.
        """
        now = datetime.utcnow()

        entry = _ViolationEntry(
            timestamp=self._parse_timestamp(event.get("timestamp"), now),
            department=event.get("department", "unknown"),
            employee_id=event.get("employee_id", "unknown"),
            violation_type=event.get("violation_type", "unknown"),
            rule_id=event.get("rule_id", "unknown"),
            severity=event.get("severity", "MEDIUM"),
            details=event.get("details", {}),
        )

        self._violations.append(entry)
        self._prune_old_entries(now)

        logger.debug(
            "violation_patterns.captured",
            department=entry.department,
            violation_type=entry.violation_type,
            employee_id=entry.employee_id,
            total_tracked=len(self._violations),
        )

        return self._detect_patterns(now, entry)

    def _detect_patterns(
        self,
        now: datetime,
        new_entry: _ViolationEntry,
    ) -> list[dict[str, Any]]:
        """Detect recurring patterns triggered by the new entry.

        Args:
            now: Current timestamp.
            new_entry: The newly added violation entry.

        Returns:
            List of suggestion dicts for detected patterns.
        """
        suggestions: list[dict[str, Any]] = []
        window_start = now - timedelta(days=_PATTERN_WINDOW_DAYS)

        # Check department + violation_type pattern
        dept_type_matches = [
            v
            for v in self._violations
            if (
                v.department == new_entry.department
                and v.violation_type == new_entry.violation_type
                and v.timestamp >= window_start
            )
        ]

        if len(dept_type_matches) >= _REPEAT_THRESHOLD:
            suggestions.append(self._build_department_suggestion(new_entry, dept_type_matches))

        # Check per-employee pattern (same employee, same violation type)
        employee_matches = [
            v
            for v in self._violations
            if (
                v.employee_id == new_entry.employee_id
                and v.violation_type == new_entry.violation_type
                and v.timestamp >= window_start
            )
        ]

        if len(employee_matches) >= _REPEAT_THRESHOLD:
            suggestions.append(self._build_employee_suggestion(new_entry, employee_matches))

        if suggestions:
            logger.info(
                "violation_patterns.suggestions_generated",
                suggestion_count=len(suggestions),
                department=new_entry.department,
                violation_type=new_entry.violation_type,
            )

        return suggestions

    def _build_department_suggestion(
        self,
        entry: _ViolationEntry,
        matches: list[_ViolationEntry],
    ) -> dict[str, Any]:
        """Build a rule refinement suggestion for a department-level pattern.

        Args:
            entry: The triggering violation entry.
            matches: All matching violations in the window.

        Returns:
            Suggestion dict.
        """
        unique_employees = len({m.employee_id for m in matches})

        suggestion_text = self._generate_suggestion_text(
            entry.department, entry.violation_type, len(matches), unique_employees
        )

        return {
            "type": "rule_refinement",
            "suggestion": suggestion_text,
            "evidence_count": len(matches),
            "pattern_description": (
                f"Department '{entry.department}' has had {len(matches)} "
                f"'{entry.violation_type}' violations in the last "
                f"{_PATTERN_WINDOW_DAYS} days across {unique_employees} employee(s)."
            ),
            "department": entry.department,
            "violation_type": entry.violation_type,
            "rule_id": entry.rule_id,
            "unique_employees": unique_employees,
            "window_days": _PATTERN_WINDOW_DAYS,
        }

    def _build_employee_suggestion(
        self,
        entry: _ViolationEntry,
        matches: list[_ViolationEntry],
    ) -> dict[str, Any]:
        """Build a suggestion for a recurring individual violation pattern.

        Args:
            entry: The triggering violation entry.
            matches: All matching violations for this employee.

        Returns:
            Suggestion dict.
        """
        return {
            "type": "rule_refinement",
            "suggestion": (
                f"Employee '{entry.employee_id}' in department '{entry.department}' "
                f"has repeatedly violated '{entry.violation_type}' ({len(matches)} times "
                f"in {_PATTERN_WINDOW_DAYS} days). Consider individual intervention or "
                "adding a pre-approval gate for this employee."
            ),
            "evidence_count": len(matches),
            "pattern_description": (
                f"Employee '{entry.employee_id}' has {len(matches)} "
                f"'{entry.violation_type}' violations in {_PATTERN_WINDOW_DAYS} days."
            ),
            "department": entry.department,
            "violation_type": entry.violation_type,
            "rule_id": entry.rule_id,
            "employee_id": entry.employee_id,
            "window_days": _PATTERN_WINDOW_DAYS,
        }

    @staticmethod
    def _generate_suggestion_text(
        department: str,
        violation_type: str,
        count: int,
        unique_employees: int,
    ) -> str:
        """Generate human-readable suggestion text based on violation pattern.

        Args:
            department: Department with the pattern.
            violation_type: Type of recurring violation.
            count: Number of violations in the window.
            unique_employees: Number of distinct employees involved.

        Returns:
            Suggestion text string.
        """
        suggestions_map: dict[str, str] = {
            "monthly_overtime_cap": (
                f"Department '{department}' consistently violates the 45h monthly "
                f"overtime cap ({count} violations). Consider adding a pre-approval "
                "requirement at 35h to prevent limit breaches."
            ),
            "consecutive_work_days": (
                f"Department '{department}' repeatedly exceeds consecutive work day "
                f"limits ({count} violations). Consider implementing mandatory "
                "scheduling checks that block assignments beyond day 5."
            ),
            "break_requirement": (
                f"Department '{department}' has recurring break time violations "
                f"({count} violations across {unique_employees} employees). "
                "Consider adding automated break reminders or system-enforced "
                "minimum break periods."
            ),
            "late_night_work": (
                f"Department '{department}' frequently has unapproved late-night work "
                f"({count} occurrences). Consider requiring advance approval for "
                "any work scheduled past 21:00."
            ),
        }

        if violation_type in suggestions_map:
            return suggestions_map[violation_type]

        return (
            f"Department '{department}' has a recurring pattern of "
            f"'{violation_type}' violations ({count} in {_PATTERN_WINDOW_DAYS} days, "
            f"{unique_employees} employee(s)). Consider tightening the threshold "
            "or adding a pre-approval step."
        )

    def _prune_old_entries(self, now: datetime) -> None:
        """Remove violations older than the retention window.

        Args:
            now: Current timestamp for calculating cutoff.
        """
        cutoff = now - timedelta(days=_RETENTION_DAYS)
        original_count = len(self._violations)
        self._violations = [v for v in self._violations if v.timestamp >= cutoff]

        pruned = original_count - len(self._violations)
        if pruned > 0:
            logger.debug(
                "violation_patterns.pruned",
                pruned_count=pruned,
                remaining_count=len(self._violations),
            )

    @staticmethod
    def _parse_timestamp(value: Any, default: datetime) -> datetime:
        """Parse a timestamp value into a datetime.

        Args:
            value: Timestamp string, datetime, or None.
            default: Default value if parsing fails.

        Returns:
            Parsed datetime.
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return default
