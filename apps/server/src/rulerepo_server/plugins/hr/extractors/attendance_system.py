"""Attendance system extractor — extracts rules from attendance data exports.

Parses attendance CSV/JSON exports and shift schedules to detect overtime
patterns and extract implicit shift rules (standard work hours, break
requirements, core time patterns). Produces candidate rules for
formalization.

See: CLAUDE.md SS14.11
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Thresholds for pattern detection
_CONSECUTIVE_OVERTIME_DAYS_THRESHOLD = 5
_MONTHLY_OVERTIME_WARNING_HOURS = 40.0
_MONTHLY_OVERTIME_LIMIT_HOURS = 45.0
_MAX_CONSECUTIVE_WORK_DAYS = 6
_STANDARD_BREAK_THRESHOLD_6H = 45
_STANDARD_BREAK_THRESHOLD_8H = 60


@dataclass
class _AttendanceRecord:
    """Internal representation of a single attendance record."""

    employee_id: str
    record_date: date
    clock_in: datetime | None = None
    clock_out: datetime | None = None
    break_minutes: int = 0
    overtime_hours: float = 0.0
    late_arrival: bool = False
    early_departure: bool = False


@dataclass
class _EmployeePattern:
    """Aggregated pattern data for a single employee."""

    employee_id: str
    records: list[_AttendanceRecord] = field(default_factory=list)
    monthly_overtime: dict[str, float] = field(default_factory=dict)
    consecutive_overtime_streaks: list[int] = field(default_factory=list)
    consecutive_work_day_streaks: list[int] = field(default_factory=list)
    break_violations: list[_AttendanceRecord] = field(default_factory=list)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse a datetime string in common formats.

    Args:
        value: String datetime or None.

    Returns:
        Parsed datetime or None.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_date(value: str | None) -> date | None:
    """Parse a date string.

    Args:
        value: String date or None.

    Returns:
        Parsed date or None.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_csv_records(text: str) -> list[_AttendanceRecord]:
    """Parse CSV attendance data into records.

    Args:
        text: CSV text content.

    Returns:
        List of parsed attendance records.
    """
    records: list[_AttendanceRecord] = []
    reader = csv.DictReader(io.StringIO(text))

    for row in reader:
        employee_id = row.get("employee_id", "").strip()
        record_date = _parse_date(row.get("date"))
        if not employee_id or not record_date:
            continue

        records.append(
            _AttendanceRecord(
                employee_id=employee_id,
                record_date=record_date,
                clock_in=_parse_datetime(row.get("clock_in")),
                clock_out=_parse_datetime(row.get("clock_out")),
                break_minutes=int(row.get("break_minutes", 0) or 0),
                overtime_hours=float(row.get("overtime_hours", 0.0) or 0.0),
                late_arrival=row.get("late_arrival", "").strip().lower() in ("true", "1", "yes"),
                early_departure=row.get("early_departure", "").strip().lower() in ("true", "1", "yes"),
            )
        )

    return records


def _parse_json_records(text: str) -> list[_AttendanceRecord]:
    """Parse JSON attendance data into records.

    Args:
        text: JSON text content (array of record objects).

    Returns:
        List of parsed attendance records.
    """
    records: list[_AttendanceRecord] = []
    data = json.loads(text)

    if isinstance(data, dict):
        data = data.get("records", data.get("data", []))

    for entry in data:
        employee_id = entry.get("employee_id", "")
        record_date = _parse_date(entry.get("date"))
        if not employee_id or not record_date:
            continue

        records.append(
            _AttendanceRecord(
                employee_id=employee_id,
                record_date=record_date,
                clock_in=_parse_datetime(entry.get("clock_in")),
                clock_out=_parse_datetime(entry.get("clock_out")),
                break_minutes=int(entry.get("break_minutes", 0) or 0),
                overtime_hours=float(entry.get("overtime_hours", 0.0) or 0.0),
                late_arrival=bool(entry.get("late_arrival", False)),
                early_departure=bool(entry.get("early_departure", False)),
            )
        )

    return records


def _analyze_patterns(records: list[_AttendanceRecord]) -> dict[str, _EmployeePattern]:
    """Analyze attendance records to detect patterns per employee.

    Args:
        records: All attendance records.

    Returns:
        Dict mapping employee_id to their pattern analysis.
    """
    by_employee: dict[str, list[_AttendanceRecord]] = defaultdict(list)
    for r in records:
        by_employee[r.employee_id].append(r)

    patterns: dict[str, _EmployeePattern] = {}

    for emp_id, emp_records in by_employee.items():
        emp_records.sort(key=lambda x: x.record_date)
        pattern = _EmployeePattern(employee_id=emp_id, records=emp_records)

        # Monthly overtime totals
        monthly: dict[str, float] = defaultdict(float)
        for r in emp_records:
            month_key = r.record_date.strftime("%Y-%m")
            monthly[month_key] += r.overtime_hours
        pattern.monthly_overtime = dict(monthly)

        # Consecutive overtime days
        streak = 0
        for r in emp_records:
            if r.overtime_hours > 0:
                streak += 1
            else:
                if streak >= _CONSECUTIVE_OVERTIME_DAYS_THRESHOLD:
                    pattern.consecutive_overtime_streaks.append(streak)
                streak = 0
        if streak >= _CONSECUTIVE_OVERTIME_DAYS_THRESHOLD:
            pattern.consecutive_overtime_streaks.append(streak)

        # Consecutive work days (no rest day)
        work_streak = 1
        for i in range(1, len(emp_records)):
            delta = (emp_records[i].record_date - emp_records[i - 1].record_date).days
            if delta == 1:
                work_streak += 1
            else:
                if work_streak > _MAX_CONSECUTIVE_WORK_DAYS:
                    pattern.consecutive_work_day_streaks.append(work_streak)
                work_streak = 1
        if work_streak > _MAX_CONSECUTIVE_WORK_DAYS:
            pattern.consecutive_work_day_streaks.append(work_streak)

        # Break violations
        for r in emp_records:
            if r.clock_in and r.clock_out:
                worked_minutes = (r.clock_out - r.clock_in).total_seconds() / 60
                if (worked_minutes > 480 and r.break_minutes < _STANDARD_BREAK_THRESHOLD_8H) or (
                    worked_minutes > 360 and r.break_minutes < _STANDARD_BREAK_THRESHOLD_6H
                ):
                    pattern.break_violations.append(r)

        patterns[emp_id] = pattern

    return patterns


def _detect_implicit_rules(
    records: list[_AttendanceRecord],
    patterns: dict[str, _EmployeePattern],
) -> list[dict[str, Any]]:
    """Detect implicit shift rules from attendance data patterns.

    Args:
        records: All attendance records.
        patterns: Per-employee pattern analysis.

    Returns:
        List of candidate rule dicts.
    """
    candidates: list[dict[str, Any]] = []

    # Detect standard work hours from clock_in/clock_out mode
    clock_ins: list[int] = []
    clock_outs: list[int] = []
    for r in records:
        if r.clock_in:
            clock_ins.append(r.clock_in.hour * 60 + r.clock_in.minute)
        if r.clock_out:
            clock_outs.append(r.clock_out.hour * 60 + r.clock_out.minute)

    if clock_ins:
        avg_in = sum(clock_ins) // len(clock_ins)
        in_h, in_m = divmod(avg_in, 60)
        candidates.append(
            {
                "statement": f"Standard work start time is {in_h:02d}:{in_m:02d}.",
                "modality": "SHOULD",
                "severity": "LOW",
                "scope": ["hr/attendance"],
                "tags": ["auto-extracted", "attendance", "shift-pattern", "hr"],
                "rationale": f"Detected from average clock-in time across {len(clock_ins)} records.",
                "applicable_subject_types": ["event", "transaction"],
            }
        )

    if clock_outs:
        avg_out = sum(clock_outs) // len(clock_outs)
        out_h, out_m = divmod(avg_out, 60)
        candidates.append(
            {
                "statement": f"Standard work end time is {out_h:02d}:{out_m:02d}.",
                "modality": "SHOULD",
                "severity": "LOW",
                "scope": ["hr/attendance"],
                "tags": ["auto-extracted", "attendance", "shift-pattern", "hr"],
                "rationale": f"Detected from average clock-out time across {len(clock_outs)} records.",
                "applicable_subject_types": ["event", "transaction"],
            }
        )

    # Detect overtime pattern rules
    employees_over_limit = sum(
        1 for p in patterns.values() if any(h >= _MONTHLY_OVERTIME_LIMIT_HOURS for h in p.monthly_overtime.values())
    )
    if employees_over_limit > 0:
        candidates.append(
            {
                "statement": (
                    f"Monthly overtime must not exceed {_MONTHLY_OVERTIME_LIMIT_HOURS}h "
                    "per employee (36-Agreement standard limit)."
                ),
                "modality": "MUST",
                "severity": "HIGH",
                "scope": ["hr/attendance", "hr/overtime"],
                "tags": ["auto-extracted", "attendance", "overtime", "36-agreement", "hr"],
                "rationale": (
                    f"{employees_over_limit} employee(s) found exceeding "
                    f"{_MONTHLY_OVERTIME_LIMIT_HOURS}h monthly overtime in the dataset."
                ),
                "applicable_subject_types": ["event", "transaction"],
            }
        )

    # Detect consecutive work day violations
    employees_over_consecutive = sum(1 for p in patterns.values() if p.consecutive_work_day_streaks)
    if employees_over_consecutive > 0:
        candidates.append(
            {
                "statement": (
                    f"Employees must not work more than {_MAX_CONSECUTIVE_WORK_DAYS} "
                    "consecutive days without a rest day."
                ),
                "modality": "MUST",
                "severity": "HIGH",
                "scope": ["hr/attendance"],
                "tags": ["auto-extracted", "attendance", "rest-day", "hr"],
                "rationale": (
                    f"{employees_over_consecutive} employee(s) found working more than "
                    f"{_MAX_CONSECUTIVE_WORK_DAYS} consecutive days."
                ),
                "applicable_subject_types": ["event", "transaction"],
            }
        )

    # Detect break requirement violations
    employees_with_break_issues = sum(1 for p in patterns.values() if p.break_violations)
    if employees_with_break_issues > 0:
        candidates.append(
            {
                "statement": (
                    "Employees working more than 6 hours must take at least 45 minutes break; "
                    "employees working more than 8 hours must take at least 60 minutes break."
                ),
                "modality": "MUST",
                "severity": "MEDIUM",
                "scope": ["hr/attendance"],
                "tags": ["auto-extracted", "attendance", "break-requirement", "hr"],
                "rationale": (
                    f"{employees_with_break_issues} employee(s) found with insufficient "
                    "break time relative to hours worked."
                ),
                "applicable_subject_types": ["event", "transaction"],
            }
        )

    # Detect consecutive overtime streaks
    employees_with_streaks = sum(1 for p in patterns.values() if p.consecutive_overtime_streaks)
    if employees_with_streaks > 0:
        candidates.append(
            {
                "statement": (
                    f"Employees should not have overtime on more than "
                    f"{_CONSECUTIVE_OVERTIME_DAYS_THRESHOLD} consecutive working days."
                ),
                "modality": "SHOULD",
                "severity": "MEDIUM",
                "scope": ["hr/attendance", "hr/overtime"],
                "tags": ["auto-extracted", "attendance", "overtime-pattern", "hr"],
                "rationale": (
                    f"{employees_with_streaks} employee(s) found with overtime streaks "
                    f"of {_CONSECUTIVE_OVERTIME_DAYS_THRESHOLD}+ consecutive days."
                ),
                "applicable_subject_types": ["event", "transaction"],
            }
        )

    return candidates


class AttendanceSystemExtractor:
    """Extracts implicit rules from attendance system data exports.

    Parses attendance CSV/JSON exports and shift schedules to detect
    overtime patterns, break violations, and standard work hour
    conventions. Produces candidate rules for formalization.
    """

    @property
    def name(self) -> str:
        return "attendance_system"

    @property
    def domain(self) -> str:
        return "hr"

    @property
    def supported_source_types(self) -> list[str]:
        return ["attendance_csv", "attendance_json", "shift_schedule"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract candidate rules from attendance system data.

        Args:
            content: Raw bytes of attendance data (CSV or JSON).
            source_type: One of 'attendance_csv', 'attendance_json', 'shift_schedule'.
            metadata: Additional context (filename, organization, period, ...).

        Returns:
            List of candidate rule dicts with statement, modality, severity,
            scope, tags, rationale, and applicable_subject_types.

        Raises:
            ValueError: If the source_type is not supported or content cannot be parsed.
        """
        if source_type not in self.supported_source_types:
            raise ValueError(f"Unsupported source_type '{source_type}'. Supported: {self.supported_source_types}")

        text = content.decode("utf-8", errors="replace")
        filename = metadata.get("filename", "attendance_export")

        logger.info(
            "attendance_extractor.start",
            source_type=source_type,
            filename=filename,
            content_length=len(text),
        )

        if source_type in ("attendance_csv", "shift_schedule"):
            records = _parse_csv_records(text)
        else:
            records = _parse_json_records(text)

        if not records:
            logger.warning(
                "attendance_extractor.no_records",
                source_type=source_type,
                filename=filename,
            )
            return []

        logger.info(
            "attendance_extractor.records_parsed",
            record_count=len(records),
            employee_count=len({r.employee_id for r in records}),
        )

        patterns = _analyze_patterns(records)
        candidates = _detect_implicit_rules(records, patterns)

        logger.info(
            "attendance_extractor.complete",
            candidate_count=len(candidates),
            filename=filename,
        )

        return candidates
