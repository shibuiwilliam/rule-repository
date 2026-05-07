"""Attendance system connector — webhook receiver for overtime/leave events.

Supports integration with attendance management systems (e.g., freee HR,
King of Time, SmartHR). Normalizes webhook payloads into HR_EVENT subjects.

Phase 7d. Requires API credentials configured via environment variables.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.subject import EvaluationSubject, SubjectType

logger = get_logger(__name__)


class AttendanceConnector:
    """Connector for attendance management systems."""

    @property
    def system_name(self) -> str:
        return "attendance"

    def normalize_webhook(self, payload: dict[str, Any]) -> EvaluationSubject:
        """Normalize an attendance webhook into an HR_EVENT subject.

        Expected payload fields:
            event_type: "overtime_register" | "leave_request" | "attendance_record"
            employee_id: str
            date or month: str
            hours: float (for overtime)
            leave_type: str (for leave)
            leave_days: int (for leave)
        """
        return EvaluationSubject(
            type=SubjectType.HR_EVENT,
            payload={
                "event_type": payload.get("event_type", "attendance_record"),
                "employee_id": payload.get("employee_id", ""),
                "date": payload.get("date", payload.get("month", "")),
                "hours": payload.get("hours", payload.get("overtime_hours")),
                "leave_type": payload.get("leave_type"),
                "leave_days": payload.get("leave_days"),
                "location": payload.get("location", "jp"),
            },
            metadata={
                "source_system": self.system_name,
                "webhook_id": payload.get("webhook_id", ""),
            },
        )

    async def dispatch_result(
        self,
        evaluation_id: str,
        verdict: str,
        details: dict[str, Any],
    ) -> None:
        """Send evaluation result back to the attendance system."""
        # TODO: Implement outbound API call to attendance system
        # Requires: API credentials, endpoint URL from config
        logger.info(
            "attendance_dispatch_placeholder",
            evaluation_id=evaluation_id,
            verdict=verdict,
        )
