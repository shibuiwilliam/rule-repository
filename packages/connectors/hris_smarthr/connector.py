"""SmartHR HRIS connector — mock implementation.

Implements both EventSource and Sink protocols for SmartHR integration.
This mock version returns realistic sample data for development and
testing.  A production implementation would call the SmartHR REST API
(https://developer.smarthr.jp/).

Polls employee events: attendance, overtime, leave requests, status
changes.  Sends verdicts and alerts back as comments or notifications.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.services.connectors.base import (
    ConnectorConfig,
    ConnectorHealth,
    ConnectorStatus,
    EventCallback,
)

# Sample employee data for the mock.
_MOCK_EMPLOYEES: list[dict[str, Any]] = [
    {
        "id": "emp-001",
        "name": "Tanaka Yuki",
        "department": "engineering",
        "position": "senior_engineer",
        "employment_type": "full_time",
        "hire_date": "2021-04-01",
    },
    {
        "id": "emp-002",
        "name": "Suzuki Haruka",
        "department": "hr",
        "position": "hr_specialist",
        "employment_type": "full_time",
        "hire_date": "2022-07-15",
    },
    {
        "id": "emp-003",
        "name": "Sato Kenji",
        "department": "sales",
        "position": "account_executive",
        "employment_type": "contract",
        "hire_date": "2023-01-10",
    },
]


def _generate_attendance_events(since: datetime, limit: int) -> list[dict[str, Any]]:
    """Generate mock attendance events."""
    events: list[dict[str, Any]] = []
    for emp in _MOCK_EMPLOYEES[:limit]:
        events.append(
            {
                "event_type": "attendance",
                "event_id": str(uuid.uuid4()),
                "employee_id": emp["id"],
                "employee_name": emp["name"],
                "department": emp["department"],
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "date": datetime.now(UTC).strftime("%Y-%m-%d"),
                    "clock_in": "09:05:00",
                    "clock_out": "18:30:00",
                    "break_minutes": 60,
                    "work_minutes": 505,
                },
            }
        )
    return events[:limit]


def _generate_overtime_events(since: datetime, limit: int) -> list[dict[str, Any]]:
    """Generate mock overtime events."""
    return [
        {
            "event_type": "overtime",
            "event_id": str(uuid.uuid4()),
            "employee_id": "emp-001",
            "employee_name": "Tanaka Yuki",
            "department": "engineering",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "month": datetime.now(UTC).strftime("%Y-%m"),
                "overtime_hours": 42.5,
                "holiday_work_hours": 8.0,
                "late_night_hours": 4.0,
                "threshold_36agreement": 45.0,
                "remaining_annual_cap": 277.5,
            },
        }
    ][:limit]


def _generate_leave_events(since: datetime, limit: int) -> list[dict[str, Any]]:
    """Generate mock leave request events."""
    return [
        {
            "event_type": "leave_request",
            "event_id": str(uuid.uuid4()),
            "employee_id": "emp-002",
            "employee_name": "Suzuki Haruka",
            "department": "hr",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "leave_type": "paid_annual",
                "start_date": "2026-05-15",
                "end_date": "2026-05-16",
                "days_requested": 2,
                "remaining_balance": 12,
                "status": "pending",
                "reason": "Personal",
            },
        }
    ][:limit]


def _generate_status_change_events(since: datetime, limit: int) -> list[dict[str, Any]]:
    """Generate mock employee status change events."""
    return [
        {
            "event_type": "status_change",
            "event_id": str(uuid.uuid4()),
            "employee_id": "emp-003",
            "employee_name": "Sato Kenji",
            "department": "sales",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "change_type": "department_transfer",
                "from_department": "sales",
                "to_department": "business_development",
                "effective_date": "2026-06-01",
                "approved_by": "mgr-001",
            },
        }
    ][:limit]


class SmartHRConnector:
    """Mock SmartHR HRIS connector implementing EventSource and Sink.

    In production, this would authenticate via OAuth2 and call the
    SmartHR API.  The mock version generates realistic sample data for
    local development and integration testing.

    Args:
        config: Connector configuration with SmartHR-specific settings.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._subscriptions: dict[str, EventCallback] = {}

    # -- Protocol properties -----------------------------------------------

    @property
    def name(self) -> str:
        """Human-readable connector name."""
        return "SmartHR HRIS"

    @property
    def connector_type(self) -> str:
        """Machine-readable connector type."""
        return "hris-smarthr"

    @property
    def domain(self) -> str:
        """Business domain."""
        return "hr"

    # -- EventSource -------------------------------------------------------

    async def poll_events(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Poll SmartHR for employee events since *since*.

        Returns a mixed list of attendance, overtime, leave, and status
        change events.  In production, this would call
        ``GET /api/v1/employees/events?since=...``.

        Args:
            since: Return only events after this timestamp.
            limit: Maximum number of events to return.

        Returns:
            Normalized event dicts.
        """
        per_type = max(1, limit // 4)
        events: list[dict[str, Any]] = []
        events.extend(_generate_attendance_events(since, per_type))
        events.extend(_generate_overtime_events(since, per_type))
        events.extend(_generate_leave_events(since, per_type))
        events.extend(_generate_status_change_events(since, per_type))
        return events[:limit]

    async def subscribe(self, callback: EventCallback) -> str:
        """Register a webhook-style callback for real-time events.

        Args:
            callback: Async callable receiving batches of event dicts.

        Returns:
            A subscription ID for later cancellation.
        """
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = callback
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove a previously registered subscription.

        Args:
            subscription_id: The ID returned by :meth:`subscribe`.
        """
        self._subscriptions.pop(subscription_id, None)

    async def health_check(self) -> ConnectorHealth:
        """Probe SmartHR connectivity.

        The mock always returns CONNECTED with a synthetic latency.

        Returns:
            A ConnectorHealth snapshot.
        """
        start = time.monotonic()
        # In production: make a lightweight API call, e.g. GET /api/v1/me
        latency = (time.monotonic() - start) * 1000
        return ConnectorHealth(
            status=ConnectorStatus.CONNECTED,
            last_checked_at=datetime.now(UTC),
            latency_ms=round(latency, 2),
        )

    # -- Sink --------------------------------------------------------------

    async def send_verdict(self, evaluation_result: dict[str, Any]) -> bool:
        """Push an evaluation verdict to SmartHR as a comment/notification.

        In production, this would call the SmartHR notification or
        comment API to attach the verdict to the relevant employee
        record.

        Args:
            evaluation_result: Normalized evaluation result dict.

        Returns:
            True if accepted.
        """
        # Mock: always succeed.
        return True

    async def send_alert(self, alert: dict[str, Any]) -> bool:
        """Push a compliance alert to SmartHR administrators.

        Args:
            alert: Normalized alert dict.

        Returns:
            True if accepted.
        """
        return True

    async def send_notification(self, notification: dict[str, Any]) -> bool:
        """Push a general notification to SmartHR.

        Args:
            notification: Normalized notification dict.

        Returns:
            True if accepted.
        """
        return True

    # -- Additional domain methods -----------------------------------------

    async def list_employees(self) -> list[dict[str, Any]]:
        """List employees from SmartHR.

        Returns:
            A list of employee record dicts.
        """
        return list(_MOCK_EMPLOYEES)

    async def get_attendance(
        self,
        employee_id: str,
        date: str,
    ) -> dict[str, Any] | None:
        """Get attendance record for an employee on a specific date.

        Args:
            employee_id: SmartHR employee ID.
            date: Date string in ``YYYY-MM-DD`` format.

        Returns:
            Attendance record dict, or None if not found.
        """
        emp = next((e for e in _MOCK_EMPLOYEES if e["id"] == employee_id), None)
        if emp is None:
            return None
        return {
            "employee_id": employee_id,
            "date": date,
            "clock_in": "09:00:00",
            "clock_out": "18:00:00",
            "break_minutes": 60,
            "work_minutes": 480,
        }

    async def get_overtime_records(
        self,
        employee_id: str,
        month: str,
    ) -> dict[str, Any] | None:
        """Get overtime summary for an employee in a given month.

        Args:
            employee_id: SmartHR employee ID.
            month: Month string in ``YYYY-MM`` format.

        Returns:
            Overtime summary dict, or None if not found.
        """
        emp = next((e for e in _MOCK_EMPLOYEES if e["id"] == employee_id), None)
        if emp is None:
            return None
        return {
            "employee_id": employee_id,
            "month": month,
            "overtime_hours": 35.0,
            "holiday_work_hours": 0.0,
            "late_night_hours": 2.0,
        }

    async def submit_evaluation_result(
        self,
        employee_id: str,
        evaluation: dict[str, Any],
    ) -> bool:
        """Submit a rule evaluation result for an employee record.

        In production, this would create a comment or custom field
        update on the employee's SmartHR profile.

        Args:
            employee_id: SmartHR employee ID.
            evaluation: Evaluation result dict.

        Returns:
            True if the submission was accepted.
        """
        return True
