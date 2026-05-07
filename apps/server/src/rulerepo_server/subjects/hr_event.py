"""Event subject adapter — handles attendance, overtime, leave evaluations.

Evaluates HR and operations business events against labor and policy rules.
See: CLAUDE.md §12.3
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext, HrEventRemediation
from rulerepo_server.domain.subject import PromptFormat, SubjectKind
from rulerepo_server.subjects.registry import register


@register(SubjectKind.EVENT)
class EventAdapter:
    """Adapter for event (HR / operations) evaluations."""

    kind = SubjectKind.EVENT

    @property
    def identifier(self) -> str:
        return "event"

    @property
    def subject_type(self) -> str:
        """Backward-compatible alias."""
        return self.kind.value

    def parse_payload(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse an HR event payload into an EvaluationContext."""
        return EvaluationContext(
            facts=payload,
            intent=payload.get("event_type", "event"),
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

    def render_for_llm(self, facts: dict[str, Any], format: PromptFormat = PromptFormat.FULL) -> str:
        """Format the HR event as prompt context."""
        return _build_narrative(facts)

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Legacy alias for render_for_llm."""
        return self.render_for_llm(payload)

    def extract_features(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract event-specific features for rule selection."""
        return {
            "event_type": payload.get("event_type", ""),
            "has_hours": "hours" in payload or "overtime_hours" in payload,
            "has_leave": "leave_type" in payload,
            "jurisdiction": payload.get("jurisdiction", payload.get("location", "")),
        }

    def parse_remediation(self, raw: dict[str, Any]) -> HrEventRemediation | None:
        """Parse an HR event remediation from raw LLM output."""
        action = raw.get("action_required") or raw.get("description", "")
        if not action:
            return None
        return HrEventRemediation(
            type=raw.get("type", "workflow"),
            description=raw.get("description", action),
            action_required=action,
            deadline_days=raw.get("deadline_days"),
            escalation_target=raw.get("escalation_target", ""),
            auto_applicable=False,
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        """Employee events typically contain PII."""
        pii = []
        if "employee_id" in payload:
            pii.append("employee_id")
        if "ssn" in payload:
            pii.append("ssn")
        if "employee_name" in payload:
            pii.append("employee_name")
        return pii


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


# Backward-compatible alias
HrEventAdapter = EventAdapter
