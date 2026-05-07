"""HR event subject adapter — handles attendance, overtime, leave evaluations.

Evaluates HR business events against labor rules.
See: IMPROVEMENT.md Phase 7b
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext


class HrEventAdapter:
    """Adapter for HR event evaluations."""

    @property
    def subject_type(self) -> str:
        return "hr_event"

    def parse_payload(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse an HR event payload into an EvaluationContext."""
        return EvaluationContext(
            facts=payload,
            intent=payload.get("event_type", "hr_event"),
            narrative=_build_narrative(payload),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from event type and employee attributes."""
        scopes = ["hr"]
        event_type = payload.get("event_type", "")
        if "overtime" in event_type or "attendance" in event_type:
            scopes.append("hr/attendance")
        if "leave" in event_type:
            scopes.append("hr/leave")
        if "compensation" in event_type or "salary" in event_type:
            scopes.append("hr/compensation")

        location = payload.get("location", payload.get("jurisdiction", ""))
        if location:
            scopes = [f"{s}/{location.lower()}" if "/" in s else s for s in scopes]
            scopes.append(f"hr/attendance/{location.lower()}")

        return list(dict.fromkeys(scopes))  # deduplicate preserving order

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Format the HR event as prompt context."""
        return _build_narrative(payload)


def _build_narrative(payload: dict[str, Any]) -> str:
    """Build a human-readable narrative from HR event fields."""
    parts = []
    event_type = payload.get("event_type", "unknown event")
    parts.append(f"HR Event: {event_type}")

    if "employee_id" in payload:
        parts.append(f"Employee: {payload['employee_id']}")
    if "month" in payload or "date" in payload:
        parts.append(f"Period: {payload.get('month', payload.get('date', 'unknown'))}")
    if "hours" in payload or "overtime_hours" in payload:
        hours = payload.get("hours", payload.get("overtime_hours"))
        parts.append(f"Hours: {hours}")
    if "leave_type" in payload:
        parts.append(f"Leave type: {payload['leave_type']}")
    if "leave_days" in payload:
        parts.append(f"Leave days: {payload['leave_days']}")

    # Include any remaining facts
    standard_keys = {
        "event_type",
        "employee_id",
        "month",
        "date",
        "hours",
        "overtime_hours",
        "leave_type",
        "leave_days",
        "location",
        "jurisdiction",
    }
    for k, v in payload.items():
        if k not in standard_keys:
            parts.append(f"{k}: {v}")

    return "\n".join(parts)
