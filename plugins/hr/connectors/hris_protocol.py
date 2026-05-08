"""HRIS connector protocol for the HR plugin.

Defines the canonical data structures and async interface that all
HRIS connectors (SmartHR, freee HR, Workday, SAP SuccessFactors, mock)
must implement.

See: CLAUDE.md §12.3, §13
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class HRISEvent:
    """A normalized event from an HRIS system.

    Attributes:
        event_type: Canonical event type (e.g., "overtime_record",
            "leave_request", "attendance_clock_in").
        employee_id: Unique employee identifier in the source system.
        timestamp: When the event occurred.
        payload: Source-specific details normalized to a flat dict.
    """

    event_type: str
    employee_id: str
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HRISEmployee:
    """Canonical employee record from an HRIS system.

    Attributes:
        id: Unique employee identifier.
        name: Display name.
        department: Department name or code.
        employment_type: "full_time", "part_time", "contract", "temporary".
        hire_date: Date employment began.
        grade: Job grade or level.
        manager_id: Employee ID of the direct manager, or None.
        contract_type: "indefinite", "fixed_term", "probation".
        working_hours_per_week: Contracted weekly working hours.
    """

    id: str
    name: str
    department: str
    employment_type: str
    hire_date: date
    grade: str = ""
    manager_id: str | None = None
    contract_type: str = "indefinite"
    working_hours_per_week: float = 40.0


@runtime_checkable
class HRISConnector(Protocol):
    """Protocol for HRIS system connectors.

    Each connector normalizes a source HRIS (SmartHR, freee HR, Workday,
    SAP SuccessFactors, etc.) into the canonical HRISEmployee / HRISEvent
    data structures.

    All methods are async to support both local and remote backends.
    """

    async def get_employee(self, employee_id: str) -> HRISEmployee:
        """Retrieve a single employee record.

        Args:
            employee_id: The employee's unique identifier.

        Returns:
            The canonical employee record.

        Raises:
            KeyError: If the employee does not exist.
        """
        ...

    async def get_attendance(
        self,
        employee_id: str,
        month: str,
    ) -> list[dict[str, Any]]:
        """Retrieve daily attendance records for a given month.

        Args:
            employee_id: The employee's unique identifier.
            month: Month in "YYYY-MM" format.

        Returns:
            A list of daily attendance dicts, each containing at minimum:
            ``date``, ``clock_in``, ``clock_out``, ``break_minutes``,
            ``total_hours``.
        """
        ...

    async def get_overtime(
        self,
        employee_id: str,
        month: str,
    ) -> dict[str, Any]:
        """Retrieve overtime summary for a given month.

        Args:
            employee_id: The employee's unique identifier.
            month: Month in "YYYY-MM" format.

        Returns:
            A dict containing at minimum: ``employee_id``, ``month``,
            ``total_overtime_hours``, ``weekday_overtime_hours``,
            ``holiday_work_hours``, ``late_night_hours``.
        """
        ...

    async def get_leave_balance(
        self,
        employee_id: str,
    ) -> dict[str, Any]:
        """Retrieve current leave balance and usage.

        Args:
            employee_id: The employee's unique identifier.

        Returns:
            A dict containing at minimum: ``employee_id``,
            ``annual_leave_entitled``, ``annual_leave_taken``,
            ``annual_leave_remaining``, ``carry_over_days``,
            ``special_leave_balances`` (dict of leave_type -> days).
        """
        ...

    async def list_events(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[HRISEvent]:
        """List events from the HRIS since a given timestamp.

        Args:
            since: Only return events after this timestamp.
            limit: Maximum number of events to return.

        Returns:
            A list of HRISEvent objects, ordered by timestamp ascending.
        """
        ...
