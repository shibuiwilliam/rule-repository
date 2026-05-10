"""Attendance evaluator — deterministic evaluation of attendance records.

Evaluates attendance and overtime records against Japanese labor law
rules (36-Agreement) and company policies. All checks are rule-based
(no LLM) for deterministic, auditable results.

See: CLAUDE.md SS14.4, SS14.7
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# 36-Agreement limits (standard)
_MONTHLY_LIMIT_STANDARD = 45.0
_ANNUAL_LIMIT_STANDARD = 360.0

# 36-Agreement limits (special clause)
_MONTHLY_LIMIT_SPECIAL = 100.0
_ANNUAL_LIMIT_SPECIAL = 720.0

# Consecutive work day limits
_MAX_CONSECUTIVE_DAYS_STANDARD = 6
_MAX_CONSECUTIVE_DAYS_SPECIAL = 12

# Break requirements (minutes)
_BREAK_REQUIRED_6H = 45
_BREAK_REQUIRED_8H = 60

# Late-night work window
_LATE_NIGHT_START = time(22, 0)
_LATE_NIGHT_END = time(5, 0)

# Rolling average threshold (2-6 month window)
_ROLLING_AVERAGE_LIMIT = 80.0


def _parse_time(value: str | None) -> time | None:
    """Parse a time string.

    Args:
        value: Time string (HH:MM or HH:MM:SS) or None.

    Returns:
        Parsed time or None.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _is_late_night(t: time) -> bool:
    """Check if a time falls within the late-night premium window (22:00-05:00).

    Args:
        t: Time to check.

    Returns:
        True if within late-night window.
    """
    return t >= _LATE_NIGHT_START or t < _LATE_NIGHT_END


def _compute_worked_minutes(clock_in: str | None, clock_out: str | None) -> float | None:
    """Compute total minutes worked from clock times.

    Args:
        clock_in: Clock-in time string.
        clock_out: Clock-out time string.

    Returns:
        Minutes worked, or None if times are invalid.
    """
    t_in = _parse_time(clock_in)
    t_out = _parse_time(clock_out)
    if t_in is None or t_out is None:
        return None

    dt_in = datetime.combine(date.today(), t_in)
    dt_out = datetime.combine(date.today(), t_out)

    # Handle overnight shifts
    if dt_out < dt_in:
        dt_out += timedelta(days=1)

    return (dt_out - dt_in).total_seconds() / 60


def _build_verdict(
    rule_id: str,
    verdict: str,
    confidence: float,
    reasoning: str,
    remediation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standardized verdict dict.

    Args:
        rule_id: ID of the rule being evaluated against.
        verdict: ALLOW, DENY, or NEEDS_CONFIRMATION.
        confidence: Confidence score (0.0 - 1.0).
        reasoning: Human-readable explanation.
        remediation: Optional remediation dict.

    Returns:
        Verdict dict.
    """
    result: dict[str, Any] = {
        "rule_id": rule_id,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
    }
    if remediation:
        result["remediation"] = remediation
    return result


class AttendanceEvaluator:
    """Deterministic evaluator for attendance and overtime records.

    Evaluates attendance events and transactions against HR rules
    covering Japanese labor law 36-Agreement limits, break requirements,
    consecutive work days, and late-night premium detection.

    All checks are rule-based (no LLM dependency) for deterministic
    and auditable results.
    """

    @property
    def name(self) -> str:
        return "attendance_evaluator"

    @property
    def domain(self) -> str:
        return "hr"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["event", "transaction"]

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate an attendance record against applicable HR rules.

        Runs deterministic checks for:
        - 36-Agreement monthly overtime cap (45h standard / configurable special)
        - 36-Agreement annual overtime cap (360h standard / 720h special)
        - Consecutive work days (max 6 / 12 for special periods)
        - Break requirements (45min for 6-8h, 60min for 8h+)
        - Late-night premium detection (22:00-05:00)
        - Rolling average overtime (2-6 month window, must stay under 80h/month)

        Args:
            subject_payload: Attendance event/transaction data containing fields
                such as overtime_hours, clock_in, clock_out, break_minutes,
                consecutive_work_days, monthly_overtime_history, etc.
            rules: List of applicable HR rule dicts.
            context: Additional context (special_clause_active, special_clause_limit,
                rolling_window_months, etc.).

        Returns:
            List of verdict dicts with rule_id, verdict, confidence, reasoning,
            and optional remediation.
        """
        logger.info(
            "attendance_evaluator.start",
            event_type=subject_payload.get("event_type"),
            employee_id=subject_payload.get("employee_id"),
            rule_count=len(rules),
        )

        verdicts: list[dict[str, Any]] = []

        verdicts.extend(self._check_monthly_overtime(subject_payload, rules, context))
        verdicts.extend(self._check_annual_overtime(subject_payload, rules, context))
        verdicts.extend(self._check_consecutive_days(subject_payload, rules, context))
        verdicts.extend(self._check_break_requirements(subject_payload, rules, context))
        verdicts.extend(self._check_late_night(subject_payload, rules, context))
        verdicts.extend(self._check_rolling_average(subject_payload, rules, context))

        logger.info(
            "attendance_evaluator.complete",
            verdict_count=len(verdicts),
            deny_count=sum(1 for v in verdicts if v["verdict"] == "DENY"),
        )

        return verdicts

    def _check_monthly_overtime(
        self,
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check 36-Agreement monthly overtime cap.

        Args:
            payload: Subject payload.
            rules: Applicable rules.
            context: Evaluation context.

        Returns:
            List of verdicts for monthly overtime check.
        """
        verdicts: list[dict[str, Any]] = []

        current_monthly = float(payload.get("monthly_overtime_total", 0.0))
        new_overtime = float(payload.get("overtime_hours", 0.0))
        projected = current_monthly + new_overtime

        special_clause = context.get("special_clause_active", False)
        limit = (
            float(context.get("special_clause_limit", _MONTHLY_LIMIT_SPECIAL))
            if special_clause
            else _MONTHLY_LIMIT_STANDARD
        )

        matching_rules = self._find_rules_by_scope(rules, ["hr/overtime", "hr/attendance"])
        rule_id = matching_rules[0].get("id", "36-agreement-monthly") if matching_rules else "36-agreement-monthly"

        if projected > limit:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="DENY",
                    confidence=1.0,
                    reasoning=(
                        f"Monthly overtime would reach {projected:.1f}h, exceeding the "
                        f"{'special clause ' if special_clause else ''}limit of {limit:.1f}h. "
                        f"Current month total: {current_monthly:.1f}h + requested: {new_overtime:.1f}h."
                    ),
                    remediation={
                        "kind": "block",
                        "description": (f"Block overtime request. Monthly total would exceed {limit:.1f}h limit."),
                        "auto_applicable": True,
                    },
                )
            )
        elif projected > limit * 0.9:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="NEEDS_CONFIRMATION",
                    confidence=0.9,
                    reasoning=(
                        f"Monthly overtime approaching limit: {projected:.1f}h / {limit:.1f}h "
                        f"({projected / limit * 100:.0f}%). Manager approval recommended."
                    ),
                    remediation={
                        "kind": "approval_add",
                        "description": "Require manager approval for overtime near monthly cap.",
                        "auto_applicable": False,
                        "payload": {"approver_role": "manager", "reason": "overtime_near_cap"},
                    },
                )
            )
        else:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="ALLOW",
                    confidence=1.0,
                    reasoning=f"Monthly overtime within limit: {projected:.1f}h / {limit:.1f}h.",
                )
            )

        return verdicts

    def _check_annual_overtime(
        self,
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check 36-Agreement annual overtime cap.

        Args:
            payload: Subject payload.
            rules: Applicable rules.
            context: Evaluation context.

        Returns:
            List of verdicts for annual overtime check.
        """
        verdicts: list[dict[str, Any]] = []

        ytd_overtime = float(payload.get("annual_overtime_total", 0.0))
        new_overtime = float(payload.get("overtime_hours", 0.0))
        projected = ytd_overtime + new_overtime

        special_clause = context.get("special_clause_active", False)
        limit = _ANNUAL_LIMIT_SPECIAL if special_clause else _ANNUAL_LIMIT_STANDARD

        matching_rules = self._find_rules_by_scope(rules, ["hr/overtime"])
        rule_id = matching_rules[0].get("id", "36-agreement-annual") if matching_rules else "36-agreement-annual"

        if projected > limit:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="DENY",
                    confidence=1.0,
                    reasoning=(
                        f"Annual overtime would reach {projected:.1f}h, exceeding the "
                        f"{'special clause ' if special_clause else ''}annual limit of {limit:.1f}h."
                    ),
                    remediation={
                        "kind": "block",
                        "description": f"Block overtime. Annual total would exceed {limit:.1f}h.",
                        "auto_applicable": True,
                    },
                )
            )
        elif projected > limit * 0.85:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="NEEDS_CONFIRMATION",
                    confidence=0.9,
                    reasoning=(
                        f"Annual overtime approaching limit: {projected:.1f}h / {limit:.1f}h "
                        f"({projected / limit * 100:.0f}%)."
                    ),
                    remediation={
                        "kind": "approval_add",
                        "description": "Require HR director approval for overtime near annual cap.",
                        "auto_applicable": False,
                        "payload": {"approver_role": "hr_director", "reason": "overtime_near_annual_cap"},
                    },
                )
            )
        else:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="ALLOW",
                    confidence=1.0,
                    reasoning=f"Annual overtime within limit: {projected:.1f}h / {limit:.1f}h.",
                )
            )

        return verdicts

    def _check_consecutive_days(
        self,
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check consecutive work days limit.

        Args:
            payload: Subject payload.
            rules: Applicable rules.
            context: Evaluation context.

        Returns:
            List of verdicts for consecutive days check.
        """
        verdicts: list[dict[str, Any]] = []

        consecutive_days = int(payload.get("consecutive_work_days", 0))
        if consecutive_days == 0:
            return verdicts

        special_period = context.get("special_period_active", False)
        limit = _MAX_CONSECUTIVE_DAYS_SPECIAL if special_period else _MAX_CONSECUTIVE_DAYS_STANDARD

        matching_rules = self._find_rules_by_scope(rules, ["hr/attendance"])
        rule_id = matching_rules[0].get("id", "consecutive-work-days") if matching_rules else "consecutive-work-days"

        if consecutive_days >= limit:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="DENY",
                    confidence=1.0,
                    reasoning=(
                        f"Employee has worked {consecutive_days} consecutive days, "
                        f"reaching or exceeding the limit of {limit} days. "
                        "A rest day is legally required."
                    ),
                    remediation={
                        "kind": "block",
                        "description": "Block work assignment. Rest day required.",
                        "auto_applicable": True,
                    },
                )
            )
        elif consecutive_days >= limit - 1:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="NEEDS_CONFIRMATION",
                    confidence=0.95,
                    reasoning=(
                        f"Employee has worked {consecutive_days} consecutive days. "
                        f"Next day would reach the {limit}-day limit."
                    ),
                    remediation={
                        "kind": "field_change",
                        "description": "Schedule a rest day within the next working day.",
                        "auto_applicable": False,
                        "payload": {"field": "next_rest_day", "suggested_value": "next_available"},
                    },
                )
            )

        return verdicts

    def _check_break_requirements(
        self,
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check break time requirements based on hours worked.

        Args:
            payload: Subject payload.
            rules: Applicable rules.
            context: Evaluation context.

        Returns:
            List of verdicts for break requirement check.
        """
        verdicts: list[dict[str, Any]] = []

        worked_minutes = _compute_worked_minutes(
            payload.get("clock_in"),
            payload.get("clock_out"),
        )
        if worked_minutes is None:
            return verdicts

        break_minutes = int(payload.get("break_minutes", 0))
        matching_rules = self._find_rules_by_scope(rules, ["hr/attendance"])
        rule_id = matching_rules[0].get("id", "break-requirement") if matching_rules else "break-requirement"

        if worked_minutes > 480 and break_minutes < _BREAK_REQUIRED_8H:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="DENY",
                    confidence=1.0,
                    reasoning=(
                        f"Work duration is {worked_minutes:.0f} minutes (>8h) but break is "
                        f"only {break_minutes} minutes. Minimum {_BREAK_REQUIRED_8H} minutes required."
                    ),
                    remediation={
                        "kind": "field_change",
                        "description": (f"Increase break time to at least {_BREAK_REQUIRED_8H} minutes."),
                        "auto_applicable": False,
                        "payload": {
                            "field": "break_minutes",
                            "current_value": break_minutes,
                            "required_minimum": _BREAK_REQUIRED_8H,
                        },
                    },
                )
            )
        elif worked_minutes > 360 and break_minutes < _BREAK_REQUIRED_6H:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="DENY",
                    confidence=1.0,
                    reasoning=(
                        f"Work duration is {worked_minutes:.0f} minutes (>6h) but break is "
                        f"only {break_minutes} minutes. Minimum {_BREAK_REQUIRED_6H} minutes required."
                    ),
                    remediation={
                        "kind": "field_change",
                        "description": (f"Increase break time to at least {_BREAK_REQUIRED_6H} minutes."),
                        "auto_applicable": False,
                        "payload": {
                            "field": "break_minutes",
                            "current_value": break_minutes,
                            "required_minimum": _BREAK_REQUIRED_6H,
                        },
                    },
                )
            )

        return verdicts

    def _check_late_night(
        self,
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Detect late-night work (22:00-05:00) requiring premium pay.

        Args:
            payload: Subject payload.
            rules: Applicable rules.
            context: Evaluation context.

        Returns:
            List of verdicts for late-night detection.
        """
        verdicts: list[dict[str, Any]] = []

        clock_out = _parse_time(payload.get("clock_out"))
        clock_in = _parse_time(payload.get("clock_in"))

        has_late_night = False
        if clock_out and _is_late_night(clock_out):
            has_late_night = True
        if clock_in and _is_late_night(clock_in):
            has_late_night = True

        if not has_late_night:
            return verdicts

        matching_rules = self._find_rules_by_scope(rules, ["hr/overtime", "hr/attendance"])
        rule_id = matching_rules[0].get("id", "late-night-premium") if matching_rules else "late-night-premium"

        verdicts.append(
            _build_verdict(
                rule_id=rule_id,
                verdict="NEEDS_CONFIRMATION",
                confidence=0.95,
                reasoning=(
                    "Work detected during late-night hours (22:00-05:00). "
                    "Late-night premium (25%+) applies. Verify approval and pay calculation."
                ),
                remediation={
                    "kind": "approval_add",
                    "description": "Ensure late-night work approval and premium pay is applied.",
                    "auto_applicable": False,
                    "payload": {
                        "approver_role": "manager",
                        "reason": "late_night_work",
                        "premium_rate": 0.25,
                    },
                },
            )
        )

        return verdicts

    def _check_rolling_average(
        self,
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check 2-6 month rolling average overtime (must stay under 80h/month).

        Args:
            payload: Subject payload.
            rules: Applicable rules.
            context: Evaluation context.

        Returns:
            List of verdicts for rolling average check.
        """
        verdicts: list[dict[str, Any]] = []

        monthly_history = payload.get("monthly_overtime_history")
        if not isinstance(monthly_history, list) or len(monthly_history) < 2:
            return verdicts

        window_months = int(context.get("rolling_window_months", 6))
        recent = monthly_history[-window_months:]

        new_overtime = float(payload.get("overtime_hours", 0.0))
        current_monthly = float(payload.get("monthly_overtime_total", 0.0))
        projected_current = current_monthly + new_overtime

        # Include the projected current month in the average
        window_values = recent + [projected_current]
        # Use the most recent N months (up to window size)
        if len(window_values) > window_months:
            window_values = window_values[-window_months:]

        rolling_avg = sum(window_values) / len(window_values)

        matching_rules = self._find_rules_by_scope(rules, ["hr/overtime"])
        rule_id = (
            matching_rules[0].get("id", "rolling-average-overtime") if matching_rules else "rolling-average-overtime"
        )

        if rolling_avg > _ROLLING_AVERAGE_LIMIT:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="DENY",
                    confidence=1.0,
                    reasoning=(
                        f"Rolling {len(window_values)}-month average overtime is {rolling_avg:.1f}h/month, "
                        f"exceeding the {_ROLLING_AVERAGE_LIMIT:.0f}h/month limit. "
                        "This is a health and safety violation."
                    ),
                    remediation={
                        "kind": "block",
                        "description": (
                            f"Block overtime. Rolling average ({rolling_avg:.1f}h) exceeds "
                            f"{_ROLLING_AVERAGE_LIMIT:.0f}h limit."
                        ),
                        "auto_applicable": True,
                    },
                )
            )
        elif rolling_avg > _ROLLING_AVERAGE_LIMIT * 0.9:
            verdicts.append(
                _build_verdict(
                    rule_id=rule_id,
                    verdict="NEEDS_CONFIRMATION",
                    confidence=0.85,
                    reasoning=(
                        f"Rolling average overtime is {rolling_avg:.1f}h/month, approaching "
                        f"the {_ROLLING_AVERAGE_LIMIT:.0f}h/month limit."
                    ),
                    remediation={
                        "kind": "approval_add",
                        "description": "Require occupational health review for sustained high overtime.",
                        "auto_applicable": False,
                        "payload": {
                            "approver_role": "occupational_health",
                            "reason": "rolling_average_near_limit",
                        },
                    },
                )
            )

        return verdicts

    @staticmethod
    def _find_rules_by_scope(
        rules: list[dict[str, Any]],
        target_scopes: list[str],
    ) -> list[dict[str, Any]]:
        """Find rules matching any of the target scopes.

        Args:
            rules: List of rule dicts.
            target_scopes: Scopes to match against.

        Returns:
            List of matching rules.
        """
        matching: list[dict[str, Any]] = []
        for rule in rules:
            rule_scopes = rule.get("scope", [])
            if isinstance(rule_scopes, str):
                rule_scopes = [rule_scopes]
            if any(s in rule_scopes for s in target_scopes):
                matching.append(rule)
        return matching
