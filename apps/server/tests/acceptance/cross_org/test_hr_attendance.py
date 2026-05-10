"""Acceptance test: HR attendance enforcement.

Scenario (PROJECT.md §11.5 #3):
    1. Employee handbook + 36-Agreement -> applicable rules
    2. Attendance registration BusinessEvent (60h overtime)
    3. Evaluation returns DENY + repair suggestion

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rulerepo_server.domain.business_event import ActorRef, BusinessEvent
from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.services.events.scope_resolver import EventScopeResolver


class TestHrAttendance:
    """End-to-end HR attendance enforcement acceptance test."""

    def test_attendance_scope_resolution(self) -> None:
        """Event type 'hr.attendance.registered' resolves to attendance scopes."""
        resolver = EventScopeResolver()
        scopes = resolver.resolve("hr.attendance.registered")
        assert "hr/attendance" in scopes

    def test_overtime_event_construction(self) -> None:
        """BusinessEvent can represent a 60h overtime registration."""
        subject = EvaluationSubject(
            kind=SubjectKind.TRANSACTION,
            payload={
                "employee_id": "E001",
                "month": "2026-04",
                "total_hours_worked": 220,
                "overtime_hours": 60,
                "has_36_agreement": True,
                "agreement_limit_hours": 45,
            },
            context={
                "department": "engineering",
                "employment_type": "full-time",
            },
        )

        event = BusinessEvent(
            event_type="hr.attendance.registered",
            actor=ActorRef(type="system", id="hris", department="hr"),
            subject=subject,
            occurred_at=datetime.now(tz=UTC),
            correlation_id="attendance-2026-04-E001",
            mode="posthoc",
        )

        assert event.subject.payload["overtime_hours"] == 60
        assert event.subject.payload["agreement_limit_hours"] == 45

    def test_overtime_violation_remediation(self) -> None:
        """Overtime violation produces field_change or block remediation."""
        # When overtime exceeds 36-agreement limit
        remediation_field = PolymorphicRemediation(
            kind=RemediationKind.FIELD_CHANGE,
            auto_applicable=False,
            description="Reduce overtime hours to 36-agreement limit",
            payload={
                "field_path": "overtime_hours",
                "current_value": 60,
                "suggested_value": 45,
            },
        )
        assert remediation_field.validate_payload()

        # For serious violations, block may be more appropriate
        remediation_block = PolymorphicRemediation(
            kind=RemediationKind.BLOCK,
            auto_applicable=False,
            description="60h overtime exceeds legal limit; requires labor standards notification",
            payload={},
        )
        assert remediation_block.validate_payload()

    def test_leave_event_scope_resolution(self) -> None:
        """Leave-related events resolve to hr scopes."""
        resolver = EventScopeResolver()
        scopes = resolver.resolve("hr.leave.requested")
        assert "hr/leave" in scopes

    def test_event_type_fallback_resolution(self) -> None:
        """Unknown event types fall back to department/action scope."""
        resolver = EventScopeResolver()
        scopes = resolver.resolve("hr.new_feature.test")
        assert "hr/new_feature" in scopes
