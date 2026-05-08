"""HR form evaluator — evaluates HR events against labor and policy rules.

Handles overtime, leave, attendance, and compensation events. Supports
single-event evaluation, monthly sequence windows, and annual calendar
context for cumulative threshold checks.

See: CLAUDE.md SS12.3
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]


def _build_event_narrative(payload: dict[str, Any]) -> str:
    """Build a human-readable narrative from HR event fields.

    Includes temporal context from event_window (sequence mode) and
    calendar_context (calendar mode) when present.

    Args:
        payload: HR event payload.

    Returns:
        Formatted narrative string.
    """
    parts: list[str] = []
    event_type = payload.get("event_type", "unknown event")
    parts.append(f"HR Event: {event_type}")

    mode = payload.get("evaluation_mode", "single")
    parts.append(f"Evaluation Mode: {mode}")

    if "employee_id" in payload:
        parts.append(f"Employee: {payload['employee_id']}")
    if "department" in payload:
        parts.append(f"Department: {payload['department']}")
    if "employment_type" in payload:
        parts.append(f"Employment Type: {payload['employment_type']}")

    if "month" in payload or "date" in payload:
        parts.append(f"Period: {payload.get('month', payload.get('date', 'unknown'))}")

    if "hours" in payload or "overtime_hours" in payload:
        hours = payload.get("hours", payload.get("overtime_hours"))
        parts.append(f"Hours (this event): {hours}")

    if "leave_type" in payload:
        parts.append(f"Leave Type: {payload['leave_type']}")
    if "leave_days" in payload:
        parts.append(f"Leave Days: {payload['leave_days']}")

    if "location" in payload or "jurisdiction" in payload:
        loc = payload.get("location", payload.get("jurisdiction", ""))
        parts.append(f"Location/Jurisdiction: {loc}")

    # Sequence context: monthly accumulations
    event_window = payload.get("event_window")
    if isinstance(event_window, dict):
        parts.append("\n--- Monthly Context (Event Window) ---")
        parts.append(f"Window: {event_window.get('start_date', '?')} to {event_window.get('end_date', '?')}")
        aggregates = event_window.get("aggregates", {})
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

    # Remaining payload fields
    standard_keys = {
        "event_type",
        "employee_id",
        "department",
        "employment_type",
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


def _format_rules_for_prompt(rules: list[dict[str, Any]]) -> str:
    """Format rules into a prompt-friendly text block.

    Args:
        rules: List of rule dicts.

    Returns:
        Formatted rules text.
    """
    parts: list[str] = []
    for i, rule in enumerate(rules, 1):
        parts.append(
            f"Rule {i} (ID: {rule.get('id', 'unknown')}):\n"
            f"  Statement: {rule.get('statement', '')}\n"
            f"  Modality: {rule.get('modality', 'MUST')}\n"
            f"  Severity: {rule.get('severity', 'MEDIUM')}\n"
            f"  Jurisdiction: {rule.get('jurisdiction', 'global')}"
        )
    return "\n\n".join(parts)


def _parse_verdict_response(
    response_text: str,
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse LLM response into per-rule verdict dicts.

    Args:
        response_text: Raw LLM response.
        rules: Rules that were evaluated.

    Returns:
        List of verdict dicts.
    """
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "verdicts" in parsed:
            return parsed["verdicts"]
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    return [
        {
            "rule_id": rule.get("id", "unknown"),
            "verdict": "NEEDS_CONFIRMATION",
            "confidence": 0.5,
            "reasoning": "Automated parsing of LLM response failed. Manual review required.",
            "raw_response": response_text[:500],
        }
        for rule in rules
    ]


class FormEvaluator:
    """Evaluator for HR events (overtime, leave, attendance) against HR rules.

    Formats employee event context including temporal windows and
    calendar aggregates for LLM-backed evaluation. Supports Japan
    labor law specifics (36 Agreement, monthly/annual overtime limits).

    Args:
        llm_callable: Async function that takes a prompt and returns a response.
        prompt_template: Optional custom prompt template.
    """

    def __init__(
        self,
        llm_callable: LLMCallable | None = None,
        prompt_template: str | None = None,
    ) -> None:
        self._llm_callable = llm_callable
        self._prompt_template = prompt_template or self._load_default_prompt()

    @property
    def name(self) -> str:
        return "form_evaluator"

    @property
    def domain(self) -> str:
        return "hr"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["event"]

    def set_llm_callable(self, llm_callable: LLMCallable) -> None:
        """Set the LLM callable after construction.

        Args:
            llm_callable: Async function for LLM calls.
        """
        self._llm_callable = llm_callable

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate an HR event against HR rules.

        Args:
            subject_payload: HR event data (event_type, hours, employee_id, ...).
            rules: List of HR rule dicts.
            context: Additional context (locale, jurisdiction, ...).

        Returns:
            List of verdict dicts, one per rule.

        Raises:
            PluginError: If no LLM callable is configured.
        """
        from rulerepo_server.plugins.base import PluginError

        if self._llm_callable is None:
            raise PluginError("FormEvaluator requires an LLM callable. Call set_llm_callable() before evaluate().")

        narrative = _build_event_narrative(subject_payload)
        rules_text = _format_rules_for_prompt(rules)

        jurisdiction = (
            subject_payload.get("jurisdiction")
            or subject_payload.get("location")
            or context.get("jurisdiction", "global")
        )

        prompt = self._prompt_template.format(
            event_narrative=narrative,
            rules=rules_text,
            jurisdiction=jurisdiction,
            evaluation_mode=subject_payload.get("evaluation_mode", "single"),
        )

        response_text = await self._llm_callable(prompt)
        return _parse_verdict_response(response_text, rules)

    @staticmethod
    def _load_default_prompt() -> str:
        """Load the default form evaluation prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "form_evaluation.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        return (
            "You are an HR compliance assistant evaluating an employee event "
            "against HR and labor rules.\n\n"
            "## Event Details\n{event_narrative}\n\n"
            "## Jurisdiction\n{jurisdiction}\n\n"
            "## Evaluation Mode\n{evaluation_mode}\n\n"
            "## Rules to Evaluate\n{rules}\n\n"
            "For each rule, return a JSON verdict object.\n"
            "Return a JSON array of verdict objects."
        )
