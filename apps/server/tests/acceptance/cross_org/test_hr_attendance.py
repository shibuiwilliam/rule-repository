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
from rulerepo_server.domain.evaluation import EvaluationContext, Verdict
from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.scope import DOMAIN_KEY, SUBJECT_TYPE_KEY, matches_scope_dimensions
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.services.evaluation.context_assembler import assemble_context_from_subject
from rulerepo_server.services.evaluation.kind_dispatch import evaluate_local, partition_by_kind
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

    # ------------------------------------------------------------------
    # Polymorphic context assembly (Proposal 1)
    # ------------------------------------------------------------------

    def test_context_assembly_from_attendance_subject(self) -> None:
        """assemble_context_from_subject builds transaction context for attendance."""
        subject = EvaluationSubject(
            kind=SubjectKind.TRANSACTION,
            payload={
                "overtime_hours": 60,
                "agreement_limit_hours": 45,
                "employee_id": "E001",
            },
        )
        ctx = assemble_context_from_subject(subject)

        assert ctx.surface == "transaction"
        assert ctx.diff is None
        assert ctx.facts["overtime_hours"] == 60
        # Transaction narrative should include the JSON payload
        assert "60" in (ctx.narrative or "")

    # ------------------------------------------------------------------
    # Structured scope (Proposal 2)
    # ------------------------------------------------------------------

    def test_hr_attendance_scope_matches(self) -> None:
        """An hr/attendance rule matches hr attendance query dimensions."""
        rule_scope = {DOMAIN_KEY: "hr", SUBJECT_TYPE_KEY: "attendance"}
        query_dims = {DOMAIN_KEY: "hr", SUBJECT_TYPE_KEY: "attendance"}
        assert matches_scope_dimensions(rule_scope, query_dims) is True

    def test_hr_rule_does_not_match_finance(self) -> None:
        """An HR rule does not match a finance query."""
        rule_scope = {DOMAIN_KEY: "hr", SUBJECT_TYPE_KEY: "attendance"}
        query_dims = {DOMAIN_KEY: "finance"}
        assert matches_scope_dimensions(rule_scope, query_dims) is False

    # ------------------------------------------------------------------
    # Kind dispatch: computational overtime check (Proposal 3)
    # ------------------------------------------------------------------

    def test_computational_overtime_rule_denies(self) -> None:
        """A COMPUTATIONAL 45-hour overtime cap rule denies 60h without LLM."""
        rule = {
            "id": "r-overtime-45",
            "kind": "computational",
            "statement": "Monthly overtime hours MUST NOT exceed 45 hours.",
            "modality": "MUST_NOT",
            "severity": "HIGH",
        }
        ctx = EvaluationContext(
            facts={"overtime_hours": 60},
            surface="transaction",
        )

        llm_rules, local_rules = partition_by_kind([rule])
        assert len(local_rules) == 1

        verdict, model_id, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY
        assert model_id == "local/kind-dispatch"
        assert "60" in (verdict.issue_description or verdict.reasoning)

    def test_computational_overtime_rule_allows(self) -> None:
        """A COMPUTATIONAL 45-hour rule allows 30h overtime."""
        rule = {
            "id": "r-overtime-45",
            "kind": "computational",
            "statement": "Monthly overtime hours MUST NOT exceed 45 hours.",
            "modality": "MUST_NOT",
            "severity": "HIGH",
        }
        ctx = EvaluationContext(
            facts={"overtime_hours": 30},
            surface="transaction",
        )

        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.ALLOW

    def test_procedural_36_agreement_rule(self) -> None:
        """A PROCEDURAL rule checks ordering: 36-agreement must precede overtime."""
        rule = {
            "id": "r-36-agreement",
            "kind": "procedural",
            "statement": "Overtime MUST NOT be assigned without a valid 36 Agreement.",
            "modality": "MUST_NOT",
            "severity": "CRITICAL",
            "preconditions": ["36 Agreement filed"],
        }

        # Steps include the precondition → ALLOW
        ctx_ok = EvaluationContext(
            facts={"steps": ["36 Agreement filed with LSIO", "Overtime assigned"]},
        )
        verdict_ok, _, _ = evaluate_local(rule, ctx_ok)
        assert verdict_ok.verdict == Verdict.ALLOW

        # Steps missing the precondition → DENY
        ctx_bad = EvaluationContext(
            facts={"steps": ["Overtime assigned without agreement"]},
        )
        verdict_bad, _, _ = evaluate_local(rule, ctx_bad)
        assert verdict_bad.verdict == Verdict.DENY

    def test_mixed_kind_batch_separates_correctly(self) -> None:
        """A batch of mixed-kind rules partitions correctly."""
        rules = [
            {"id": "r1", "kind": "normative", "statement": "General attendance policy."},
            {"id": "r2", "kind": "computational", "statement": "Overtime MUST NOT exceed 45 hours."},
            {"id": "r3", "kind": "procedural", "statement": "36 Agreement required before overtime."},
            {"id": "r4", "kind": "definitional", "statement": "Overtime means hours beyond 8h/day."},
        ]
        llm_rules, local_rules = partition_by_kind(rules)
        assert [r["id"] for r in llm_rules] == ["r1"]
        assert [r["id"] for r in local_rules] == ["r2", "r3", "r4"]
