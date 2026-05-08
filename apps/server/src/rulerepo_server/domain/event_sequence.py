"""Domain types for event sequence and calendar evaluation.

Provides EventWindow and SequenceContext for temporal reasoning
in the Event Engine.

See: CLAUDE.md §12.3, PROJECT.md §6.3.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class EventEvaluationMode(StrEnum):
    """Evaluation mode for the Event Engine.

    - SINGLE: evaluate the event alone
    - SEQUENCE: provide windowed prior events as context (monthly accumulations)
    - CALENDAR: provide annual aggregates (yearly ceilings, threshold activations)
    """

    SINGLE = "single"
    SEQUENCE = "sequence"
    CALENDAR = "calendar"


@dataclass(frozen=True)
class EventRecord:
    """A historical event record for sequence/calendar context.

    Attributes:
        event_type: Type of event (overtime_register, leave_request, etc.).
        date: Date of the event.
        hours: Hours associated (overtime hours, work hours, etc.).
        leave_days: Number of leave days (for leave events).
        metadata: Additional event-specific data.
    """

    event_type: str
    date: date
    hours: float = 0.0
    leave_days: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EventWindow:
    """A time-bounded window of prior events for sequence evaluation.

    Used in sequence mode to provide monthly accumulations as context.

    Attributes:
        start_date: Beginning of the window.
        end_date: End of the window.
        events: Historical events within the window.
        aggregates: Pre-computed aggregates (e.g., total_overtime_hours).
    """

    start_date: date
    end_date: date
    events: list[EventRecord] = field(default_factory=list)
    aggregates: dict[str, float] = field(default_factory=dict)

    @property
    def total_hours(self) -> float:
        """Sum of hours across all events in the window."""
        return sum(e.hours for e in self.events)

    @property
    def total_leave_days(self) -> float:
        """Sum of leave days across all events in the window."""
        return sum(e.leave_days for e in self.events)

    @property
    def event_count(self) -> int:
        """Number of events in the window."""
        return len(self.events)


@dataclass(frozen=True)
class CalendarContext:
    """Annual calendar context for calendar-aware evaluation.

    Used in calendar mode to evaluate against yearly ceilings
    (e.g., 720-hour annual overtime cap, 36-Agreement thresholds).

    Attributes:
        fiscal_year: Fiscal year (e.g., 2026).
        fiscal_year_start: Start date of the fiscal year.
        fiscal_year_end: End date of the fiscal year.
        ytd_overtime_hours: Year-to-date overtime hours.
        ytd_leave_days: Year-to-date leave days taken.
        monthly_overtime: Monthly overtime breakdown.
        special_clause_active: Whether a 36-Agreement special clause is active.
        special_clause_limit: Special clause overtime limit (if active).
        agreements: Active labor agreements (36-Agreement, etc.).
    """

    fiscal_year: int
    fiscal_year_start: date
    fiscal_year_end: date
    ytd_overtime_hours: float = 0.0
    ytd_leave_days: float = 0.0
    monthly_overtime: dict[str, float] = field(default_factory=dict)
    special_clause_active: bool = False
    special_clause_limit: float = 0.0
    agreements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SequenceContext:
    """Combined context for sequence and calendar evaluation.

    Wraps both EventWindow (monthly/short-term) and CalendarContext
    (annual) for the evaluation pipeline.

    Attributes:
        mode: The evaluation mode.
        event_window: Monthly event window (for sequence mode).
        calendar_context: Annual calendar context (for calendar mode).
        employee_id: Employee identifier for context lookup.
    """

    mode: EventEvaluationMode
    event_window: EventWindow | None = None
    calendar_context: CalendarContext | None = None
    employee_id: str = ""
