"""Tests for Phase 7b subject adapters.

Verifies that each subject adapter correctly parses payloads,
resolves scopes, and formats prompt context.
"""

from __future__ import annotations

from rulerepo_server.domain.subject import EvaluationSubject, LegalForce, SubjectType
from rulerepo_server.subjects.code_change import CodeChangeAdapter
from rulerepo_server.subjects.contract_clause import ContractClauseAdapter
from rulerepo_server.subjects.expense_claim import ExpenseClaimAdapter
from rulerepo_server.subjects.hr_event import HrEventAdapter
from rulerepo_server.subjects.registry import get_adapter, register_adapter


class TestSubjectType:
    def test_enum_values(self) -> None:
        assert SubjectType.CODE_CHANGE == "code_change"
        assert SubjectType.HR_EVENT == "hr_event"
        assert SubjectType.CONTRACT_CLAUSE == "contract_clause"
        assert SubjectType.EXPENSE_CLAIM == "expense_claim"

    def test_legal_force_values(self) -> None:
        assert LegalForce.STATUTORY == "statutory"
        assert LegalForce.POLICY == "policy"


class TestEvaluationSubject:
    def test_from_legacy_diff(self) -> None:
        subject = EvaluationSubject.from_legacy_diff("--- a/foo.py\n+++ b/foo.py")
        assert subject.type == SubjectType.CODE_CHANGE
        assert subject.payload["diff"] == "--- a/foo.py\n+++ b/foo.py"

    def test_create_hr_event(self) -> None:
        subject = EvaluationSubject(
            type=SubjectType.HR_EVENT,
            payload={"event_type": "overtime_register", "employee_id": "E001", "hours": 50},
        )
        assert subject.type == SubjectType.HR_EVENT
        assert subject.payload["hours"] == 50


class TestCodeChangeAdapter:
    def test_subject_type(self) -> None:
        adapter = CodeChangeAdapter()
        assert adapter.subject_type == "code_change"

    def test_parse_payload(self) -> None:
        adapter = CodeChangeAdapter()
        ctx = adapter.parse_payload({"diff": "test diff", "intent": "fix bug"})
        assert ctx.diff == "test diff"
        assert ctx.intent == "fix bug"

    def test_resolve_scopes_from_list(self) -> None:
        adapter = CodeChangeAdapter()
        scopes = adapter.resolve_scopes({"scope": ["engineering/python"]})
        assert scopes == ["engineering/python"]

    def test_resolve_scopes_from_string(self) -> None:
        adapter = CodeChangeAdapter()
        scopes = adapter.resolve_scopes({"scope": "engineering"})
        assert scopes == ["engineering"]

    def test_format_prompt_context(self) -> None:
        adapter = CodeChangeAdapter()
        ctx = adapter.format_prompt_context({"diff": "line1\nline2"})
        assert "line1" in ctx


class TestHrEventAdapter:
    def test_subject_type(self) -> None:
        assert HrEventAdapter().subject_type == "hr_event"

    def test_parse_payload(self) -> None:
        adapter = HrEventAdapter()
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
        adapter = HrEventAdapter()
        scopes = adapter.resolve_scopes(
            {
                "event_type": "overtime_register",
                "location": "jp",
            }
        )
        assert "hr" in scopes
        assert "hr/attendance/jp" in scopes

    def test_resolve_scopes_leave(self) -> None:
        adapter = HrEventAdapter()
        scopes = adapter.resolve_scopes({"event_type": "leave_request"})
        assert "hr/leave" in scopes

    def test_format_prompt_context(self) -> None:
        adapter = HrEventAdapter()
        ctx = adapter.format_prompt_context(
            {
                "event_type": "overtime_register",
                "employee_id": "E001",
                "hours": 50,
            }
        )
        assert "overtime_register" in ctx
        assert "50" in ctx


class TestContractClauseAdapter:
    def test_subject_type(self) -> None:
        assert ContractClauseAdapter().subject_type == "contract_clause"

    def test_resolve_scopes_nda(self) -> None:
        adapter = ContractClauseAdapter()
        scopes = adapter.resolve_scopes({"contract_type": "NDA", "governing_law": "JP"})
        assert "legal/contracts/nda" in scopes
        assert "legal/contracts/jp" in scopes

    def test_parse_payload(self) -> None:
        adapter = ContractClauseAdapter()
        ctx = adapter.parse_payload(
            {
                "contract_type": "NDA",
                "clause_text": "All information is confidential.",
            }
        )
        assert ctx.intent == "contract_review"
        assert "clause_text" in ctx.facts


class TestExpenseClaimAdapter:
    def test_subject_type(self) -> None:
        assert ExpenseClaimAdapter().subject_type == "expense_claim"

    def test_resolve_scopes_entertainment(self) -> None:
        adapter = ExpenseClaimAdapter()
        scopes = adapter.resolve_scopes(
            {
                "expense_type": "entertainment",
                "jurisdiction": "jp",
            }
        )
        assert "finance/entertainment" in scopes
        assert "compliance/anti-bribery" in scopes
        assert "finance/expenses/jp" in scopes

    def test_format_prompt_context(self) -> None:
        adapter = ExpenseClaimAdapter()
        ctx = adapter.format_prompt_context(
            {
                "expense_type": "travel",
                "amount": 45000,
                "currency": "JPY",
            }
        )
        assert "45000" in ctx
        assert "JPY" in ctx


class TestRegistry:
    def test_register_and_get(self) -> None:
        adapter = CodeChangeAdapter()
        register_adapter(adapter)
        retrieved = get_adapter("code_change")
        assert retrieved is adapter

    def test_get_missing(self) -> None:
        assert get_adapter("nonexistent_type") is None
