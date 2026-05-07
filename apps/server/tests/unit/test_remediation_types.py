"""Tests for Phase 7b Remediation subclasses."""

from __future__ import annotations

from rulerepo_server.domain.evaluation import (
    CodeRemediation,
    ContractClauseRemediation,
    ExpenseRemediation,
    HrEventRemediation,
    Remediation,
    WorkflowRemediation,
)


class TestRemediationSubclasses:
    def test_base_remediation(self) -> None:
        r = Remediation(type="replace", description="Fix the issue")
        assert r.type == "replace"
        assert r.auto_applicable is False

    def test_code_remediation_inherits(self) -> None:
        r = CodeRemediation(
            type="replace",
            file_path="src/main.py",
            start_line=10,
            end_line=12,
            original="old code",
            replacement="new code",
            auto_applicable=True,
        )
        assert isinstance(r, Remediation)
        assert r.file_path == "src/main.py"
        assert r.auto_applicable is True

    def test_contract_clause_remediation(self) -> None:
        r = ContractClauseRemediation(
            type="clause_revision",
            clause_id="art3.sec2",
            revised_text="The confidentiality period shall be 3 years.",
            requires_counterparty_consent=True,
            description="Specify confidentiality duration",
        )
        assert isinstance(r, Remediation)
        assert r.clause_id == "art3.sec2"
        assert r.requires_counterparty_consent is True

    def test_hr_event_remediation(self) -> None:
        r = HrEventRemediation(
            type="workflow",
            action_required="obtain_36_agreement",
            deadline_days=5,
            escalation_target="department_head",
            description="File 36 Agreement before assigning overtime",
        )
        assert isinstance(r, Remediation)
        assert r.action_required == "obtain_36_agreement"
        assert r.deadline_days == 5

    def test_expense_remediation(self) -> None:
        r = ExpenseRemediation(
            type="workflow",
            required_documentation="original_receipt",
            approval_level="cfo",
            description="Claims over 300,000 JPY require CFO approval",
        )
        assert isinstance(r, Remediation)
        assert r.approval_level == "cfo"

    def test_workflow_remediation(self) -> None:
        r = WorkflowRemediation(
            type="workflow",
            workflow_type="approval",
            assignee="compliance_officer",
            priority="high",
            description="Route to compliance for review",
        )
        assert isinstance(r, Remediation)
        assert r.workflow_type == "approval"
        assert r.priority == "high"
