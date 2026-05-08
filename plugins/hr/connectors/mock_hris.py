"""Mock HRIS connector for development and testing.

Provides realistic sample data for a small set of mock employees,
including edge cases useful for testing overtime limits, probation
periods, and 36-agreement special clause scenarios.

See: CLAUDE.md §12.3
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from plugins.hr.connectors.hris_protocol import HRISConnector, HRISEmployee, HRISEvent

JST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# Mock employee roster
# ---------------------------------------------------------------------------

_EMPLOYEES: dict[str, HRISEmployee] = {
    "E001": HRISEmployee(
        id="E001",
        name="Tanaka Ichiro",
        department="engineering",
        employment_type="full_time",
        hire_date=date(2020, 4, 1),
        grade="M2",
        manager_id="E010",
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
    "E002": HRISEmployee(
        id="E002",
        name="Suzuki Hanako",
        department="sales",
        employment_type="full_time",
        hire_date=date(2024, 10, 1),
        grade="J1",
        manager_id="E010",
        contract_type="probation",
        working_hours_per_week=40.0,
    ),
    "E003": HRISEmployee(
        id="E003",
        name="Sato Yuki",
        department="hr",
        employment_type="part_time",
        hire_date=date(2022, 7, 15),
        grade="P1",
        manager_id="E010",
        contract_type="indefinite",
        working_hours_per_week=24.0,
    ),
    "E004": HRISEmployee(
        id="E004",
        name="Yamamoto Kenji",
        department="engineering",
        employment_type="full_time",
        hire_date=date(2019, 4, 1),
        grade="S3",
        manager_id="E010",
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
    "E005": HRISEmployee(
        id="E005",
        name="Watanabe Sakura",
        department="legal",
        employment_type="full_time",
        hire_date=date(2021, 1, 10),
        grade="M1",
        manager_id="E010",
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
    "E006": HRISEmployee(
        id="E006",
        name="Takahashi Ryo",
        department="engineering",
        employment_type="contract",
        hire_date=date(2023, 4, 1),
        grade="C2",
        manager_id="E004",
        contract_type="fixed_term",
        working_hours_per_week=40.0,
    ),
    "E007": HRISEmployee(
        id="E007",
        name="Ito Misa",
        department="finance",
        employment_type="full_time",
        hire_date=date(2018, 4, 1),
        grade="M3",
        manager_id="E010",
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
    "E008": HRISEmployee(
        id="E008",
        name="Nakamura Daiki",
        department="engineering",
        employment_type="full_time",
        hire_date=date(2023, 10, 1),
        grade="J2",
        manager_id="E004",
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
    "E009": HRISEmployee(
        id="E009",
        name="Kobayashi Aoi",
        department="marketing",
        employment_type="full_time",
        hire_date=date(2022, 4, 1),
        grade="M1",
        manager_id="E010",
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
    "E010": HRISEmployee(
        id="E010",
        name="Kato Masahiro",
        department="engineering",
        employment_type="full_time",
        hire_date=date(2015, 4, 1),
        grade="D1",
        manager_id=None,
        contract_type="indefinite",
        working_hours_per_week=40.0,
    ),
}

# ---------------------------------------------------------------------------
# Pre-built overtime data (edge cases)
# ---------------------------------------------------------------------------


def _build_overtime(
    employee_id: str,
    month: str,
    total: float,
    weekday: float | None = None,
    holiday: float = 0.0,
    late_night: float = 0.0,
) -> dict[str, Any]:
    return {
        "employee_id": employee_id,
        "month": month,
        "total_overtime_hours": total,
        "weekday_overtime_hours": weekday if weekday is not None else total - holiday,
        "holiday_work_hours": holiday,
        "late_night_hours": late_night,
    }


# E004 is near the monthly 45h limit
# E001 has moderate overtime
# E007 is near the annual 360h limit (tracked via cumulative)
_OVERTIME: dict[tuple[str, str], dict[str, Any]] = {
    ("E001", "2026-04"): _build_overtime("E001", "2026-04", 25.0, holiday=4.0),
    ("E001", "2026-03"): _build_overtime("E001", "2026-03", 30.0),
    ("E004", "2026-04"): _build_overtime("E004", "2026-04", 43.5, holiday=8.0, late_night=6.0),
    ("E004", "2026-03"): _build_overtime("E004", "2026-03", 44.0, holiday=8.0, late_night=4.0),
    ("E007", "2026-04"): _build_overtime("E007", "2026-04", 38.0),
    ("E007", "2026-03"): _build_overtime("E007", "2026-03", 40.0),
    ("E006", "2026-04"): _build_overtime("E006", "2026-04", 10.0),
    ("E002", "2026-04"): _build_overtime("E002", "2026-04", 5.0),
}

# ---------------------------------------------------------------------------
# Pre-built leave balances
# ---------------------------------------------------------------------------

_LEAVE: dict[str, dict[str, Any]] = {
    "E001": {
        "employee_id": "E001",
        "annual_leave_entitled": 20,
        "annual_leave_taken": 8,
        "annual_leave_remaining": 12,
        "carry_over_days": 5,
        "special_leave_balances": {"sick": 10, "bereavement": 5},
    },
    "E002": {
        "employee_id": "E002",
        "annual_leave_entitled": 10,
        "annual_leave_taken": 1,
        "annual_leave_remaining": 9,
        "carry_over_days": 0,
        "special_leave_balances": {"sick": 10},
    },
    "E003": {
        "employee_id": "E003",
        "annual_leave_entitled": 12,
        "annual_leave_taken": 3,
        "annual_leave_remaining": 9,
        "carry_over_days": 2,
        "special_leave_balances": {"sick": 5},
    },
    "E004": {
        "employee_id": "E004",
        "annual_leave_entitled": 20,
        "annual_leave_taken": 2,
        "annual_leave_remaining": 18,
        "carry_over_days": 8,
        "special_leave_balances": {"sick": 10, "bereavement": 5},
    },
    "E005": {
        "employee_id": "E005",
        "annual_leave_entitled": 16,
        "annual_leave_taken": 12,
        "annual_leave_remaining": 4,
        "carry_over_days": 3,
        "special_leave_balances": {"sick": 10, "bereavement": 5},
    },
    "E006": {
        "employee_id": "E006",
        "annual_leave_entitled": 12,
        "annual_leave_taken": 6,
        "annual_leave_remaining": 6,
        "carry_over_days": 0,
        "special_leave_balances": {"sick": 5},
    },
    "E007": {
        "employee_id": "E007",
        "annual_leave_entitled": 20,
        "annual_leave_taken": 3,
        "annual_leave_remaining": 17,
        "carry_over_days": 10,
        "special_leave_balances": {"sick": 10, "bereavement": 5, "childcare": 5},
    },
    "E008": {
        "employee_id": "E008",
        "annual_leave_entitled": 10,
        "annual_leave_taken": 0,
        "annual_leave_remaining": 10,
        "carry_over_days": 0,
        "special_leave_balances": {"sick": 10},
    },
    "E009": {
        "employee_id": "E009",
        "annual_leave_entitled": 14,
        "annual_leave_taken": 7,
        "annual_leave_remaining": 7,
        "carry_over_days": 4,
        "special_leave_balances": {"sick": 10, "bereavement": 5},
    },
    "E010": {
        "employee_id": "E010",
        "annual_leave_entitled": 20,
        "annual_leave_taken": 15,
        "annual_leave_remaining": 5,
        "carry_over_days": 5,
        "special_leave_balances": {"sick": 10, "bereavement": 5},
    },
}

# ---------------------------------------------------------------------------
# Attendance helper
# ---------------------------------------------------------------------------


def _generate_attendance(
    employee_id: str,
    month: str,
    base_hours: float = 8.0,
    break_minutes: int = 60,
    work_days: int = 20,
) -> list[dict[str, Any]]:
    """Generate synthetic daily attendance records for a month."""
    year, mon = (int(x) for x in month.split("-"))
    records: list[dict[str, Any]] = []
    d = date(year, mon, 1)
    count = 0
    while d.month == mon and count < work_days:
        if d.weekday() < 5:  # Monday-Friday
            records.append(
                {
                    "date": d.isoformat(),
                    "clock_in": "09:00",
                    "clock_out": f"{9 + int(base_hours) + 1}:00",
                    "break_minutes": break_minutes,
                    "total_hours": base_hours,
                }
            )
            count += 1
        d += timedelta(days=1)
    return records


# ---------------------------------------------------------------------------
# MockHRISConnector
# ---------------------------------------------------------------------------


class MockHRISConnector:
    """In-memory HRIS connector for development and testing.

    Implements the ``HRISConnector`` protocol with a small, deterministic
    dataset that includes edge cases for overtime limits, probation
    periods, and 36-agreement special clause scenarios.
    """

    def __init__(self) -> None:
        self._employees = dict(_EMPLOYEES)
        self._overtime = dict(_OVERTIME)
        self._leave = dict(_LEAVE)
        self._events: list[HRISEvent] = _build_sample_events()

    async def get_employee(self, employee_id: str) -> HRISEmployee:
        """Retrieve a mock employee record.

        Raises:
            KeyError: If employee_id is not in the mock roster.
        """
        if employee_id not in self._employees:
            raise KeyError(f"Employee not found: {employee_id}")
        return self._employees[employee_id]

    async def get_attendance(
        self,
        employee_id: str,
        month: str,
    ) -> list[dict[str, Any]]:
        """Return synthetic attendance data for the requested month."""
        if employee_id not in self._employees:
            raise KeyError(f"Employee not found: {employee_id}")
        emp = self._employees[employee_id]
        daily_hours = emp.working_hours_per_week / 5.0
        return _generate_attendance(
            employee_id,
            month,
            base_hours=daily_hours,
            break_minutes=60 if daily_hours > 6 else 45,
        )

    async def get_overtime(
        self,
        employee_id: str,
        month: str,
    ) -> dict[str, Any]:
        """Return overtime summary for the requested month."""
        if employee_id not in self._employees:
            raise KeyError(f"Employee not found: {employee_id}")
        key = (employee_id, month)
        if key in self._overtime:
            return self._overtime[key]
        return _build_overtime(employee_id, month, 0.0)

    async def get_leave_balance(
        self,
        employee_id: str,
    ) -> dict[str, Any]:
        """Return leave balance for the employee."""
        if employee_id not in self._employees:
            raise KeyError(f"Employee not found: {employee_id}")
        if employee_id in self._leave:
            return self._leave[employee_id]
        return {
            "employee_id": employee_id,
            "annual_leave_entitled": 10,
            "annual_leave_taken": 0,
            "annual_leave_remaining": 10,
            "carry_over_days": 0,
            "special_leave_balances": {},
        }

    async def list_events(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[HRISEvent]:
        """Return events after the given timestamp, up to limit."""
        filtered = [e for e in self._events if e.timestamp > since]
        filtered.sort(key=lambda e: e.timestamp)
        return filtered[:limit]


def _build_sample_events() -> list[HRISEvent]:
    """Build a set of sample HRIS events for testing."""
    base = datetime(2026, 4, 1, 9, 0, 0, tzinfo=JST)
    events: list[HRISEvent] = [
        HRISEvent(
            event_type="overtime_record",
            employee_id="E004",
            timestamp=base + timedelta(days=10, hours=10),
            payload={
                "hours": 3.5,
                "reason": "release_deadline",
                "approved_by": "E010",
            },
        ),
        HRISEvent(
            event_type="leave_request",
            employee_id="E001",
            timestamp=base + timedelta(days=5),
            payload={
                "leave_type": "annual",
                "start_date": "2026-04-15",
                "end_date": "2026-04-16",
                "days": 2,
            },
        ),
        HRISEvent(
            event_type="leave_request",
            employee_id="E005",
            timestamp=base + timedelta(days=3),
            payload={
                "leave_type": "maternity_prenatal",
                "start_date": "2026-05-01",
                "end_date": "2026-06-11",
                "days": 42,
            },
        ),
        HRISEvent(
            event_type="attendance_anomaly",
            employee_id="E008",
            timestamp=base + timedelta(days=7, hours=2),
            payload={
                "anomaly_type": "missing_clock_out",
                "date": "2026-04-08",
            },
        ),
        HRISEvent(
            event_type="overtime_record",
            employee_id="E004",
            timestamp=base + timedelta(days=15, hours=11),
            payload={
                "hours": 4.0,
                "reason": "incident_response",
                "approved_by": "E010",
            },
        ),
        HRISEvent(
            event_type="contract_renewal",
            employee_id="E006",
            timestamp=base + timedelta(days=20),
            payload={
                "renewal_number": 3,
                "new_end_date": "2027-03-31",
                "contract_years_total": 4,
            },
        ),
        HRISEvent(
            event_type="health_check_due",
            employee_id="E004",
            timestamp=base + timedelta(days=12),
            payload={
                "reason": "overtime_threshold_exceeded",
                "monthly_overtime": 43.5,
                "threshold": 40,
            },
        ),
        HRISEvent(
            event_type="probation_ending",
            employee_id="E002",
            timestamp=base + timedelta(days=25),
            payload={
                "probation_start": "2024-10-01",
                "probation_end": "2025-03-31",
                "status": "pending_review",
            },
        ),
    ]
    return events
