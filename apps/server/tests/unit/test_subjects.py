"""Tests for subject adapters.

Verifies that each subject adapter correctly parses payloads,
resolves scopes, and formats prompt context.
"""

from __future__ import annotations

from rulerepo_server.domain.subject import EvaluationSubject, LegalForce, SubjectKind
from rulerepo_server.subjects.code_change import CodeDiffAdapter
from rulerepo_server.subjects.contract_clause import ClauseSetAdapter
from rulerepo_server.subjects.expense_claim import TransactionAdapter
from rulerepo_server.subjects.hr_event import EventAdapter
from rulerepo_server.subjects.registry import get_adapter, resolve


class TestSubjectKind:
    def test_enum_values(self) -> None:
        assert SubjectKind.CODE_DIFF == "code_diff"
        assert SubjectKind.EVENT == "event"
        assert SubjectKind.CLAUSE_SET == "clause_set"
        assert SubjectKind.TRANSACTION == "transaction"

    def test_legal_force_values(self) -> None:
        assert LegalForce.STATUTORY == "statutory"
        assert LegalForce.POLICY == "policy"


class TestEvaluationSubject:
    def test_from_legacy_diff(self) -> None:
        subject = EvaluationSubject.from_legacy_diff("--- a/foo.py\n+++ b/foo.py")
        assert subject.kind == SubjectKind.CODE_DIFF
        assert subject.payload["diff"] == "--- a/foo.py\n+++ b/foo.py"

    def test_create_event(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.EVENT,
            payload={"event_type": "overtime_register", "employee_id": "E001", "hours": 50},
        )
        assert subject.kind == SubjectKind.EVENT
        assert subject.payload["hours"] == 50

    def test_type_alias(self) -> None:
        """Backward-compat: .type property returns .kind."""
        subject = EvaluationSubject(kind=SubjectKind.CODE_DIFF)
        assert subject.type == SubjectKind.CODE_DIFF


class TestCodeDiffAdapter:
    def test_subject_type(self) -> None:
        adapter = CodeDiffAdapter()
        assert adapter.kind == SubjectKind.CODE_DIFF
        assert adapter.subject_type == "code_diff"

    def test_parse_payload(self) -> None:
        adapter = CodeDiffAdapter()
        ctx = adapter.parse_payload({"diff": "test diff", "intent": "fix bug"})
        assert ctx.diff == "test diff"
        assert ctx.intent == "fix bug"

    def test_resolve_scopes_from_list(self) -> None:
        adapter = CodeDiffAdapter()
        scopes = adapter.resolve_scopes({"scope": ["engineering/python"]})
        assert scopes == ["engineering/python"]

    def test_resolve_scopes_from_string(self) -> None:
        adapter = CodeDiffAdapter()
        scopes = adapter.resolve_scopes({"scope": "engineering"})
        assert scopes == ["engineering"]

    def test_render_for_llm(self) -> None:
        adapter = CodeDiffAdapter()
        ctx = adapter.render_for_llm({"diff": "line1\nline2"})
        assert "line1" in ctx


class TestEventAdapter:
    def test_subject_type(self) -> None:
        assert EventAdapter().kind == SubjectKind.EVENT
        assert EventAdapter().subject_type == "event"

    def test_parse_payload(self) -> None:
        adapter = EventAdapter()
        ctx = adapter.parse_payload(
            {
                "event_type": "overtime_register",
                "employee_id": "E001",
                "hours": 50,
                "month": "2026-04",
            }
        )
        assert ctx.intent == "overtime_register"
        assert ctx.facts["hours"] == 50

    def test_resolve_scopes_overtime(self) -> None:
        adapter = EventAdapter()
        scopes = adapter.resolve_scopes(
            {
                "event_type": "overtime_register",
                "location": "jp",
            }
        )
        assert "hr" in scopes
        assert "hr/attendance/jp" in scopes

    def test_resolve_scopes_leave(self) -> None:
        adapter = EventAdapter()
        scopes = adapter.resolve_scopes({"event_type": "leave_request"})
        assert "hr/leave" in scopes

    def test_render_for_llm(self) -> None:
        adapter = EventAdapter()
        ctx = adapter.render_for_llm(
            {
                "event_type": "overtime_register",
                "employee_id": "E001",
                "hours": 50,
            }
        )
        assert "overtime_register" in ctx
        assert "50" in ctx

    def test_pii_fields(self) -> None:
        adapter = EventAdapter()
        pii = adapter.pii_fields({"employee_id": "E001", "ssn": "123-45"})
        assert "employee_id" in pii
        assert "ssn" in pii


class TestClauseSetAdapter:
    def test_subject_type(self) -> None:
        assert ClauseSetAdapter().kind == SubjectKind.CLAUSE_SET
        assert ClauseSetAdapter().subject_type == "clause_set"

    def test_resolve_scopes_nda(self) -> None:
        adapter = ClauseSetAdapter()
        scopes = adapter.resolve_scopes({"contract_type": "NDA", "governing_law": "JP"})
        assert "legal/contracts/nda" in scopes
        assert "legal/contracts/jp" in scopes

    def test_parse_payload(self) -> None:
        adapter = ClauseSetAdapter()
        ctx = adapter.parse_payload(
            {
                "contract_type": "NDA",
                "clause_text": "All information is confidential.",
            }
        )
        assert ctx.intent == "contract_review"
        assert "clause_text" in ctx.facts


class TestTransactionAdapter:
    def test_subject_type(self) -> None:
        assert TransactionAdapter().kind == SubjectKind.TRANSACTION
        assert TransactionAdapter().subject_type == "transaction"

    def test_resolve_scopes_entertainment(self) -> None:
        adapter = TransactionAdapter()
        scopes = adapter.resolve_scopes(
            {
                "expense_type": "entertainment",
                "jurisdiction": "jp",
            }
        )
        assert "finance/entertainment" in scopes
        assert "compliance/anti-bribery" in scopes
        assert "finance/expenses/jp" in scopes

    def test_render_for_llm(self) -> None:
        adapter = TransactionAdapter()
        ctx = adapter.render_for_llm(
            {
                "expense_type": "travel",
                "amount": 45000,
                "currency": "JPY",
            }
        )
        assert "45000" in ctx
        assert "JPY" in ctx


class TestRegistry:
    def test_resolve_code_diff(self) -> None:
        """Decorator-registered adapters can be resolved by SubjectKind."""
        adapter = resolve(SubjectKind.CODE_DIFF)
        assert adapter.kind == SubjectKind.CODE_DIFF

    def test_resolve_event(self) -> None:
        adapter = resolve(SubjectKind.EVENT)
        assert adapter.kind == SubjectKind.EVENT

    def test_resolve_clause_set(self) -> None:
        adapter = resolve(SubjectKind.CLAUSE_SET)
        assert adapter.kind == SubjectKind.CLAUSE_SET

    def test_resolve_transaction(self) -> None:
        adapter = resolve(SubjectKind.TRANSACTION)
        assert adapter.kind == SubjectKind.TRANSACTION

    def test_resolve_by_string(self) -> None:
        adapter = resolve("code_diff")
        assert adapter.kind == SubjectKind.CODE_DIFF

    def test_legacy_get_adapter(self) -> None:
        adapter = get_adapter("code_diff")
        assert adapter is not None
        assert adapter.kind == SubjectKind.CODE_DIFF

    def test_get_missing(self) -> None:
        assert get_adapter("nonexistent_type") is None
