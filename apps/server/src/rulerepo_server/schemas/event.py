"""Pydantic schemas for the Event Evaluation API.

See: CLAUDE.md §12.3, ADR 0005
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventWindowInput(BaseModel):
    """A time-bounded window of prior events for sequence evaluation."""

    start_date: str = Field(..., description="Window start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Window end date (YYYY-MM-DD)")
    events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Historical events in the window",
    )
    aggregates: dict[str, float] = Field(
        default_factory=dict,
        description="Pre-computed aggregates (e.g., total_overtime_hours)",
    )


class CalendarContextInput(BaseModel):
    """Annual calendar context for calendar-aware evaluation."""

    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_year_start: str = Field(default="", description="Fiscal year start (YYYY-MM-DD)")
    fiscal_year_end: str = Field(default="", description="Fiscal year end (YYYY-MM-DD)")
    ytd_overtime_hours: float = Field(default=0.0, description="Year-to-date overtime hours")
    ytd_leave_days: float = Field(default=0.0, description="Year-to-date leave days")
    monthly_overtime: dict[str, float] = Field(
        default_factory=dict,
        description="Monthly overtime breakdown (month → hours)",
    )
    special_clause_active: bool = Field(default=False, description="36-Agreement special clause active")
    special_clause_limit: float = Field(default=0.0, description="Special clause overtime limit")
    agreements: list[str] = Field(default_factory=list, description="Active labor agreements")


class EventEvaluateRequest(BaseModel):
    """Request to evaluate an HR/operations event against rules."""

    # Core event data
    event_type: str = Field(..., description="Event type (overtime_register, leave_request, etc.)")
    employee_id: str = Field(default="", description="Employee identifier")
    date: str = Field(default="", description="Event date (YYYY-MM-DD)")
    month: str = Field(default="", description="Event month (YYYY-MM)")
    hours: float | None = Field(default=None, description="Hours (overtime, work, etc.)")
    overtime_hours: float | None = Field(default=None, description="Overtime hours specifically")
    leave_type: str | None = Field(default=None, description="Leave type")
    leave_days: float | None = Field(default=None, description="Leave days")

    # Location/jurisdiction
    location: str = Field(default="jp", description="Location/jurisdiction")

    # Evaluation mode
    evaluation_mode: str = Field(
        default="single",
        description="Evaluation mode: single, sequence, calendar",
    )

    # Temporal context (for sequence/calendar modes)
    event_window: EventWindowInput | None = Field(
        default=None,
        description="Monthly event window (for sequence mode)",
    )
    calendar_context: CalendarContextInput | None = Field(
        default=None,
        description="Annual calendar context (for calendar mode)",
    )

    # Evaluation parameters
    mode: str = Field(default="preflight", description="preflight | posthoc")
    max_rules: int = Field(default=20, ge=1, le=100)
    severity_min: str = Field(default="MEDIUM")

    # Extra facts
    extra_facts: dict[str, Any] = Field(default_factory=dict, description="Additional facts")
