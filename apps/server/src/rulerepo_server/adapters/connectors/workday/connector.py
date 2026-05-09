"""Workday connector implementation.

Normalizes Workday HRIS events (time tracking, leave requests, personnel
changes) into HumanAction surface subjects for evaluation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class WorkdayConnector(SubjectConnector):
    """Connector for Workday HR system events."""

    @property
    def name(self) -> str:
        return "workday"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["human_action"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Workday event into a HumanAction surface subject.

        Supports event types like ``time_tracking``, ``leave_request``,
        ``personnel_change``, and ``compensation_change``.

        Args:
            event: Raw Workday event or integration payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload for the HumanAction surface.
        """
        event_type = event.get("event_type", "unknown")
        worker = event.get("worker", {})
        worker_id = worker.get("id", event.get("worker_id", "unknown"))

        return {
            "surface": "human_action",
            "identifier": f"workday:{event_type}:{worker_id}:{event.get('effective_date', '')}",
            "payload": {
                "action": event_type,
                "worker_id": worker_id,
                "department": worker.get("department", event.get("department", "")),
                "position": worker.get("position", ""),
                "effective_date": event.get("effective_date", ""),
                "details": event.get("details", {}),
                "hours": event.get("hours"),
                "leave_type": event.get("leave_type"),
            },
            "facts": {
                "source_system": "workday",
                "event_type": event_type,
                "supervisory_org": worker.get("supervisory_org", ""),
                "location": worker.get("location", ""),
            },
            "actor": {
                "kind": "human",
                "identifier": f"workday:{worker_id}",
                "attributes": {
                    "department": worker.get("department", ""),
                    "job_title": worker.get("position", ""),
                },
            },
            "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
            "locale": event.get("locale", "en"),
        }

    async def validate_connection(self) -> bool:
        """Check that Workday credentials are configured."""
        return all(os.environ.get(var) for var in ("WORKDAY_TENANT_URL", "WORKDAY_USERNAME", "WORKDAY_PASSWORD"))

    async def list_event_types(self) -> list[str]:
        return [
            "time_tracking",
            "leave_request",
            "personnel_change",
            "compensation_change",
            "termination",
            "hire",
            "transfer",
        ]
