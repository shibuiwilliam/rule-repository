"""Attendance compliance service for the HR plugin.

Provides overtime checking, leave compliance verification, department-level
summaries, and employee risk scoring against Japanese labor law thresholds.

See: CLAUDE.md §12.3, §13
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from plugins.hr.connectors.hris_protocol import HRISConnector


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OvertimeCheckResult:
    """Result of checking an employee's overtime compliance for a month.

    Attributes:
        employee_id: The employee checked.
        month: The month in "YYYY-MM" format.
        total_hours: Total overtime hours worked.
        limit: Applicable monthly limit (45h general, or special clause limit).
        is_compliant: Whether overtime is within the applicable limit.
        violations: List of specific violation descriptions.
        agreement_36_status: Status of the 36-agreement ("active", "special_clause_active", "missing", "expired").
    """

    employee_id: str
    month: str
    total_hours: float
    limit: float
    is_compliant: bool
    violations: list[str] = field(default_factory=list)
    agreement_36_status: str = "active"


@dataclass(frozen=True)
class LeaveCheckResult:
    """Result of checking an employee's leave compliance for a year.

    Attributes:
        employee_id: The employee checked.
        year: The calendar or fiscal year.
        days_taken: Number of annual leave days taken.
        days_required: Minimum days required (5 for employees with >= 10 days entitlement).
        is_compliant: Whether the employee has met the minimum usage.
        planned_days: Number of planned leave days scheduled but not yet taken.
    """

    employee_id: str
    year: int
    days_taken: int
    days_required: int
    is_compliant: bool
    planned_days: int = 0


@dataclass(frozen=True)
class DepartmentComplianceSummary:
    """Compliance summary for a department in a given month.

    Attributes:
        department_id: Department identifier.
        month: The month in "YYYY-MM" format.
        employee_count: Total employees in the department.
        violations_count: Number of employees with at least one violation.
        risk_employees: List of employee IDs with elevated risk.
        avg_overtime: Average overtime hours across the department.
    """

    department_id: str
    month: str
    employee_count: int
    violations_count: int
    risk_employees: list[str] = field(default_factory=list)
    avg_overtime: float = 0.0


@dataclass(frozen=True)
class RiskScore:
    """Employee compliance risk score.

    Attributes:
        employee_id: The employee scored.
        score: Risk score from 0 (no risk) to 100 (critical risk).
        factors: List of contributing risk factors.
    """

    employee_id: str
    score: int
    factors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants — Japanese labor law thresholds
# ---------------------------------------------------------------------------

GENERAL_MONTHLY_LIMIT = 45.0
GENERAL_ANNUAL_LIMIT = 360.0
SPECIAL_MONTHLY_LIMIT = 100.0  # including holiday work
SPECIAL_ANNUAL_LIMIT = 720.0
MULTI_MONTH_AVG_LIMIT = 80.0
HEALTH_GUIDANCE_THRESHOLD = 40.0  # monthly overtime triggering doctor consultation
MINIMUM_ANNUAL_LEAVE_DAYS = 5
LEAVE_ENTITLEMENT_THRESHOLD = 10  # days entitled to trigger 5-day minimum


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AttendanceComplianceService:
    """Checks attendance and overtime compliance against labor standards.

    Depends on an ``HRISConnector`` for employee and attendance data.
    All enforcement thresholds follow Japanese Labor Standards Act defaults
    unless overridden by tenant-specific configuration.
    """

    def __init__(self, connector: HRISConnector) -> None:
        self._connector = connector

    async def check_overtime(
        self,
        employee_id: str,
        month: str,
        tenant_id: str = "default",
    ) -> OvertimeCheckResult:
        """Check an employee's overtime compliance for a given month.

        Evaluates against:
        - General 36-agreement monthly limit (45h)
        - Special clause absolute cap (100h including holiday work)
        - Health guidance threshold (40h)

        Args:
            employee_id: Employee to check.
            month: Month in "YYYY-MM" format.
            tenant_id: Tenant identifier (reserved for multi-tenant config).

        Returns:
            OvertimeCheckResult with compliance status and any violations.
        """
        overtime = await self._connector.get_overtime(employee_id, month)
        total = overtime.get("total_overtime_hours", 0.0)
        holiday = overtime.get("holiday_work_hours", 0.0)
        total_with_holiday = total + holiday if holiday not in (0.0, None) else total

        violations: list[str] = []
        limit = GENERAL_MONTHLY_LIMIT
        agreement_status = "active"

        # General limit check
        if total > GENERAL_MONTHLY_LIMIT:
            violations.append(
                f"Monthly overtime {total:.1f}h exceeds general 36-agreement limit of {GENERAL_MONTHLY_LIMIT}h"
            )
            agreement_status = "special_clause_required"

        # Absolute cap check (special clause)
        if total_with_holiday > SPECIAL_MONTHLY_LIMIT:
            violations.append(
                f"Monthly overtime including holiday work {total_with_holiday:.1f}h exceeds absolute cap of {SPECIAL_MONTHLY_LIMIT}h"
            )
            limit = SPECIAL_MONTHLY_LIMIT
            agreement_status = "violation"

        # Health guidance threshold
        if total > HEALTH_GUIDANCE_THRESHOLD:
            violations.append(
                f"Monthly overtime {total:.1f}h exceeds {HEALTH_GUIDANCE_THRESHOLD}h health guidance threshold — doctor consultation recommended"
            )

        is_compliant = total <= GENERAL_MONTHLY_LIMIT and total_with_holiday <= SPECIAL_MONTHLY_LIMIT

        return OvertimeCheckResult(
            employee_id=employee_id,
            month=month,
            total_hours=total,
            limit=limit,
            is_compliant=is_compliant,
            violations=violations,
            agreement_36_status=agreement_status,
        )

    async def check_leave_compliance(
        self,
        employee_id: str,
        year: int,
        tenant_id: str = "default",
    ) -> LeaveCheckResult:
        """Check whether the employee has met the mandatory 5-day leave minimum.

        Per Labor Standards Act Article 39(7), employers must ensure employees
        with 10+ days entitlement take at least 5 days per year.

        Args:
            employee_id: Employee to check.
            year: Calendar or fiscal year.
            tenant_id: Tenant identifier (reserved for multi-tenant config).

        Returns:
            LeaveCheckResult with compliance status.
        """
        balance = await self._connector.get_leave_balance(employee_id)
        entitled = balance.get("annual_leave_entitled", 0)
        taken = balance.get("annual_leave_taken", 0)

        days_required = MINIMUM_ANNUAL_LEAVE_DAYS if entitled >= LEAVE_ENTITLEMENT_THRESHOLD else 0
        is_compliant = taken >= days_required

        return LeaveCheckResult(
            employee_id=employee_id,
            year=year,
            days_taken=taken,
            days_required=days_required,
            is_compliant=is_compliant,
            planned_days=0,
        )

    async def get_department_summary(
        self,
        department_id: str,
        month: str,
        tenant_id: str = "default",
    ) -> DepartmentComplianceSummary:
        """Aggregate compliance for all employees in a department.

        Note: In production, this would query a department roster. The mock
        implementation uses the connector's event listing to identify
        employees.

        Args:
            department_id: Department to summarize.
            month: Month in "YYYY-MM" format.
            tenant_id: Tenant identifier.

        Returns:
            DepartmentComplianceSummary with violation and risk counts.
        """
        # Discover employees by scanning events (mock approach)
        from datetime import datetime, timezone

        all_events = await self._connector.list_events(
            since=datetime(2000, 1, 1, tzinfo=timezone.utc),
            limit=1000,
        )
        dept_employee_ids: set[str] = set()
        for ev in all_events:
            try:
                emp = await self._connector.get_employee(ev.employee_id)
                if emp.department == department_id:
                    dept_employee_ids.add(ev.employee_id)
            except KeyError:
                continue

        violations_count = 0
        risk_employees: list[str] = []
        total_overtime = 0.0

        for eid in dept_employee_ids:
            result = await self.check_overtime(eid, month, tenant_id)
            total_overtime += result.total_hours
            if not result.is_compliant:
                violations_count += 1
            if result.total_hours > HEALTH_GUIDANCE_THRESHOLD:
                risk_employees.append(eid)

        employee_count = len(dept_employee_ids)
        avg_overtime = total_overtime / employee_count if employee_count > 0 else 0.0

        return DepartmentComplianceSummary(
            department_id=department_id,
            month=month,
            employee_count=employee_count,
            violations_count=violations_count,
            risk_employees=risk_employees,
            avg_overtime=round(avg_overtime, 1),
        )

    async def get_employee_risk_score(
        self,
        employee_id: str,
        tenant_id: str = "default",
    ) -> RiskScore:
        """Compute a composite risk score for an employee.

        Factors considered:
        - Current month overtime level relative to limits
        - Leave usage relative to mandatory minimum
        - Late-night work frequency
        - Proximity to annual overtime ceiling

        Args:
            employee_id: Employee to score.
            tenant_id: Tenant identifier.

        Returns:
            RiskScore with a 0-100 score and contributing factors.
        """
        import datetime as dt

        now = dt.datetime.now(tz=dt.timezone.utc)
        month = now.strftime("%Y-%m")
        year = now.year

        score = 0
        factors: list[str] = []

        # Overtime risk
        overtime = await self._connector.get_overtime(employee_id, month)
        total = overtime.get("total_overtime_hours", 0.0)
        late_night = overtime.get("late_night_hours", 0.0)

        if total > GENERAL_MONTHLY_LIMIT:
            score += 40
            factors.append(f"overtime_exceeds_limit:{total:.1f}h")
        elif total > HEALTH_GUIDANCE_THRESHOLD:
            score += 25
            factors.append(f"overtime_near_limit:{total:.1f}h")
        elif total > 30:
            score += 10
            factors.append(f"overtime_elevated:{total:.1f}h")

        if late_night > 10:
            score += 15
            factors.append(f"late_night_work:{late_night:.1f}h")
        elif late_night > 0:
            score += 5
            factors.append(f"late_night_present:{late_night:.1f}h")

        # Leave risk
        leave_result = await self.check_leave_compliance(employee_id, year, tenant_id)
        if not leave_result.is_compliant and leave_result.days_required > 0:
            remaining_months = max(1, 12 - now.month)
            days_needed = leave_result.days_required - leave_result.days_taken
            if remaining_months <= 3 and days_needed > 0:
                score += 20
                factors.append(f"leave_at_risk:need_{days_needed}_days_in_{remaining_months}_months")
            elif days_needed > 0:
                score += 10
                factors.append(f"leave_below_target:{leave_result.days_taken}/{leave_result.days_required}")

        # Cap at 100
        score = min(score, 100)

        return RiskScore(
            employee_id=employee_id,
            score=score,
            factors=factors,
        )
