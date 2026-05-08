"""Tests for event sequence and calendar domain types and adapter behavior.

Covers EventWindow, CalendarContext, and EventAdapter temporal modes.
"""

from __future__ import annotations

from datetime import date

from rulerepo_server.domain.event_sequence import (
    CalendarContext,
    EventEvaluationMode,
    EventRecord,
    EventWindow,
    SequenceContext,
)
from rulerepo_server.subjects.hr_event import EventAdapter

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class TestEventWindow:
    """Tests for EventWindow domain type."""

    def test_total_hours(self) -> None:
        window = EventWindow(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            events=[
                EventRecord(event_type="overtime", date=date(2026, 4, 5), hours=8.0),
                EventRecord(event_type="overtime", date=date(2026, 4, 12), hours=10.0),
                EventRecord(event_type="overtime", date=date(2026, 4, 19), hours=12.0),
            ],
        )
        assert window.total_hours == 30.0
        assert window.event_count == 3

    def test_total_leave_days(self) -> None:
        window = EventWindow(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            events=[
                EventRecord(event_type="leave", date=date(2026, 4, 10), leave_days=1.0),
                EventRecord(event_type="leave", date=date(2026, 4, 15), leave_days=0.5),
            ],
        )
        assert window.total_leave_days == 1.5

    def test_empty_window(self) -> None:
        window = EventWindow(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )
        assert window.total_hours == 0.0
        assert window.event_count == 0

    def test_aggregates(self) -> None:
        window = EventWindow(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            aggregates={"total_overtime_hours": 42.0, "working_days": 20},
        )
        assert window.aggregates["total_overtime_hours"] == 42.0


class TestCalendarContext:
    """Tests for CalendarContext domain type."""

    def test_basic_context(self) -> None:
        ctx = CalendarContext(
            fiscal_year=2026,
            fiscal_year_start=date(2026, 4, 1),
            fiscal_year_end=date(2027, 3, 31),
            ytd_overtime_hours=350.0,
            monthly_overtime={"2026-04": 45.0, "2026-05": 50.0},
            special_clause_active=True,
            special_clause_limit=100.0,
            agreements=["36-Agreement"],
        )
        assert ctx.fiscal_year == 2026
        assert ctx.ytd_overtime_hours == 350.0
        assert ctx.special_clause_active is True
        assert "36-Agreement" in ctx.agreements


class TestSequenceContext:
    """Tests for SequenceContext domain type."""

    def test_sequence_mode(self) -> None:
        window = EventWindow(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )
        ctx = SequenceContext(
            mode=EventEvaluationMode.SEQUENCE,
            event_window=window,
            employee_id="E001",
        )
        assert ctx.mode == EventEvaluationMode.SEQUENCE
        assert ctx.event_window is not None

    def test_calendar_mode(self) -> None:
        cal = CalendarContext(
            fiscal_year=2026,
            fiscal_year_start=date(2026, 4, 1),
            fiscal_year_end=date(2027, 3, 31),
        )
        ctx = SequenceContext(
            mode=EventEvaluationMode.CALENDAR,
            calendar_context=cal,
        )
        assert ctx.mode == EventEvaluationMode.CALENDAR
        assert ctx.calendar_context is not None


# ---------------------------------------------------------------------------
# EventAdapter temporal rendering
# ---------------------------------------------------------------------------


class TestEventAdapterTemporalModes:
    """Tests for EventAdapter rendering with temporal context."""

    def test_single_mode_narrative(self) -> None:
        adapter = EventAdapter()
        facts = {
            "event_type": "overtime_register",
            "employee_id": "E001",
            "hours": 10.0,
            "evaluation_mode": "single",
        }
        narrative = adapter.render_for_llm(facts)
        assert "Evaluation Mode: single" in narrative
        assert "overtime_register" in narrative
        assert "10.0" in narrative

    def test_sequence_mode_narrative(self) -> None:
        adapter = EventAdapter()
        facts = {
            "event_type": "overtime_register",
            "employee_id": "E001",
            "hours": 10.0,
            "evaluation_mode": "sequence",
            "event_window": {
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "events": [
                    {"event_type": "overtime", "hours": 15.0},
                    {"event_type": "overtime", "hours": 20.0},
                ],
                "aggregates": {"total_overtime_hours": 35.0},
            },
        }
        narrative = adapter.render_for_llm(facts)
        assert "Evaluation Mode: sequence" in narrative
        assert "Monthly Context" in narrative
        assert "total_overtime_hours: 35.0" in narrative
        assert "Prior events in window: 2" in narrative

    def test_calendar_mode_narrative(self) -> None:
        adapter = EventAdapter()
        facts = {
            "event_type": "overtime_register",
            "employee_id": "E001",
            "hours": 10.0,
            "evaluation_mode": "calendar",
            "calendar_context": {
                "fiscal_year": 2026,
                "ytd_overtime_hours": 350.0,
                "ytd_leave_days": 5.0,
                "monthly_overtime": {"2026-04": 45.0, "2026-05": 50.0},
                "special_clause_active": True,
                "special_clause_limit": 100.0,
                "agreements": ["36-Agreement"],
            },
        }
        narrative = adapter.render_for_llm(facts)
        assert "Evaluation Mode: calendar" in narrative
        assert "Annual Context" in narrative
        assert "Fiscal Year: 2026" in narrative
        assert "YTD Overtime Hours: 350.0" in narrative
        assert "36-Agreement Special Clause: ACTIVE" in narrative
        assert "2026-04: 45.0h" in narrative

    def test_extract_features_with_mode(self) -> None:
        adapter = EventAdapter()
        facts = {
            "event_type": "overtime_register",
            "hours": 10.0,
            "evaluation_mode": "sequence",
            "event_window": {"start_date": "2026-04-01", "end_date": "2026-04-30"},
        }
        features = adapter.extract_features(facts)
        assert features["evaluation_mode"] == "sequence"
        assert features["has_sequence_context"] is True
        assert features["has_calendar_context"] is False

    def test_extract_features_calendar(self) -> None:
        adapter = EventAdapter()
        facts = {
            "event_type": "overtime_register",
            "evaluation_mode": "calendar",
            "calendar_context": {"fiscal_year": 2026},
        }
        features = adapter.extract_features(facts)
        assert features["evaluation_mode"] == "calendar"
        assert features["has_calendar_context"] is True
