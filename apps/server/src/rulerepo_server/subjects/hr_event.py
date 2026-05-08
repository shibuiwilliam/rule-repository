"""Event subject adapter — handles attendance, overtime, leave evaluations.

Evaluates HR and operations business events against labor and policy rules.
Supports three evaluation modes: single, sequence, and calendar.
See: CLAUDE.md §12.3, ADR 0005
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext, HrEventRemediation
from rulerepo_server.domain.event_sequence import EventEvaluationMode
from rulerepo_server.domain.subject import PromptFormat, SubjectKind
from rulerepo_server.subjects.registry import register


@register(SubjectKind.EVENT)
class EventAdapter:
    """Adapter for event (HR / operations) evaluations.

    Supports three evaluation modes:
    - single: evaluate the event alone
    - sequence: provide windowed prior events as context (monthly accumulations)
    - calendar: provide annual aggregates (yearly ceilings)
    """

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
        """Format the HR event as prompt context, including temporal context."""
        return _build_narrative(facts)

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Legacy alias for render_for_llm."""
        return self.render_for_llm(payload)

    def extract_features(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract event-specific features for rule selection."""
        mode = payload.get("evaluation_mode", EventEvaluationMode.SINGLE)
        return {
            "event_type": payload.get("event_type", ""),
            "has_hours": "hours" in payload or "overtime_hours" in payload,
            "has_leave": "leave_type" in payload,
            "jurisdiction": payload.get("jurisdiction", payload.get("location", "")),
            "evaluation_mode": str(mode),
            "has_sequence_context": "event_window" in payload,
            "has_calendar_context": "calendar_context" in payload,
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
    """Build a human-readable narrative from HR event fields.

    Includes temporal context from event_window (sequence mode) and
    calendar_context (calendar mode) when present.
    """
    parts = []
    event_type = payload.get("event_type", "unknown event")
    mode = payload.get("evaluation_mode", "single")
    parts.append(f"HR Event: {event_type}")
    parts.append(f"Evaluation Mode: {mode}")

    if "employee_id" in payload:
        parts.append(f"Employee: {payload['employee_id']}")
    if "month" in payload or "date" in payload:
        parts.append(f"Period: {payload.get('month', payload.get('date', 'unknown'))}")
    if "hours" in payload or "overtime_hours" in payload:
        hours = payload.get("hours", payload.get("overtime_hours"))
        parts.append(f"Hours (this event): {hours}")
    if "leave_type" in payload:
        parts.append(f"Leave type: {payload['leave_type']}")
    if "leave_days" in payload:
        parts.append(f"Leave days: {payload['leave_days']}")

    # Sequence context: monthly accumulations
    event_window = payload.get("event_window")
    if isinstance(event_window, dict):
        parts.append("\n--- Monthly Context (Event Window) ---")
        parts.append(f"Window: {event_window.get('start_date', '?')} to {event_window.get('end_date', '?')}")
        aggregates = event_window.get("aggregates", {})
        if aggregates:
            for key, val in aggregates.items():
                parts.append(f"  {key}: {val}")
        window_events = event_window.get("events", [])
        if window_events:
            parts.append(f"  Prior events in window: {len(window_events)}")
            total_hours = sum(e.get("hours", 0) for e in window_events)
            parts.append(f"  Total hours in window: {total_hours}")

    # Calendar context: annual aggregates
    calendar_ctx = payload.get("calendar_context")
    if isinstance(calendar_ctx, dict):
        parts.append("\n--- Annual Context (Calendar) ---")
        parts.append(f"Fiscal Year: {calendar_ctx.get('fiscal_year', '?')}")
        parts.append(f"YTD Overtime Hours: {calendar_ctx.get('ytd_overtime_hours', 0)}")
        parts.append(f"YTD Leave Days: {calendar_ctx.get('ytd_leave_days', 0)}")
        monthly = calendar_ctx.get("monthly_overtime", {})
        if monthly:
            parts.append("Monthly overtime breakdown:")
            for month, hrs in sorted(monthly.items()):
                parts.append(f"  {month}: {hrs}h")
        if calendar_ctx.get("special_clause_active"):
            parts.append(f"36-Agreement Special Clause: ACTIVE (limit: {calendar_ctx.get('special_clause_limit', 0)}h)")
        agreements = calendar_ctx.get("agreements", [])
        if agreements:
            parts.append(f"Active agreements: {', '.join(agreements)}")

    # Include any remaining facts not already covered
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
        "evaluation_mode",
        "event_window",
        "calendar_context",
    }
    for k, v in payload.items():
        if k not in standard_keys:
            parts.append(f"{k}: {v}")

    return "\n".join(parts)


# Backward-compatible alias
HrEventAdapter = EventAdapter
