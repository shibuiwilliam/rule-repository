"""Unit tests for per-scope approval workflows (RR-021)."""

from __future__ import annotations

import pytest

from rulerepo_server.services.approval.workflows import ApprovalWorkflowService


@pytest.fixture
def svc() -> ApprovalWorkflowService:
    return ApprovalWorkflowService()


class TestApprovalWorkflowService:
    """Tests for ApprovalWorkflowService."""

    def test_engineering_low_auto_approve(self, svc: ApprovalWorkflowService) -> None:
        """Engineering LOW severity should be auto-approved."""
        assert svc.check_auto_approve("engineering/python", "LOW") is True

    def test_engineering_medium_not_auto_approved(self, svc: ApprovalWorkflowService) -> None:
        """Engineering MEDIUM severity should NOT be auto-approved."""
        assert svc.check_auto_approve("engineering/python", "MEDIUM") is False

    def test_engineering_critical_two_approvers(self, svc: ApprovalWorkflowService) -> None:
        """Engineering CRITICAL needs domain_owner + security_reviewer."""
        approvers = svc.get_required_approvers("engineering/python", "CRITICAL")
        assert approvers == ["domain_owner", "security_reviewer"]

    def test_engineering_critical_workflow_name(self, svc: ApprovalWorkflowService) -> None:
        """Engineering CRITICAL should resolve to engineering_critical workflow."""
        wf = svc.get_workflow("engineering/python", "CRITICAL")
        assert wf.name == "engineering_critical"

    def test_legal_low_requires_counsel(self, svc: ApprovalWorkflowService) -> None:
        """Legal LOW severity requires legal_counsel (compliance_officer optional)."""
        approvers = svc.get_required_approvers("legal/contracts", "LOW")
        assert "legal_counsel" in approvers
        assert "compliance_officer" not in approvers

    def test_legal_workflow_name(self, svc: ApprovalWorkflowService) -> None:
        """Legal rules should resolve to legal_standard workflow."""
        wf = svc.get_workflow("legal/contracts", "LOW")
        assert wf.name == "legal_standard"

    def test_hr_high_two_approvers(self, svc: ApprovalWorkflowService) -> None:
        """HR HIGH severity needs hr_manager + legal_counsel."""
        approvers = svc.get_required_approvers("hr/policies", "HIGH")
        assert approvers == ["hr_manager", "legal_counsel"]

    def test_hr_high_workflow_name(self, svc: ApprovalWorkflowService) -> None:
        """HR HIGH should resolve to hr_critical workflow."""
        wf = svc.get_workflow("hr/policies", "HIGH")
        assert wf.name == "hr_critical"

    def test_hr_low_single_approver(self, svc: ApprovalWorkflowService) -> None:
        """HR LOW severity needs only hr_manager."""
        approvers = svc.get_required_approvers("hr/onboarding", "LOW")
        assert approvers == ["hr_manager"]

    def test_finance_critical_two_approvers(self, svc: ApprovalWorkflowService) -> None:
        """Finance CRITICAL needs finance_controller + cfo."""
        approvers = svc.get_required_approvers("finance/reporting", "CRITICAL")
        assert approvers == ["finance_controller", "cfo"]

    def test_finance_critical_workflow_name(self, svc: ApprovalWorkflowService) -> None:
        """Finance CRITICAL should resolve to finance_critical workflow."""
        wf = svc.get_workflow("finance/reporting", "CRITICAL")
        assert wf.name == "finance_critical"

    def test_unknown_scope_default_workflow(self, svc: ApprovalWorkflowService) -> None:
        """Unknown scope falls back to the default workflow."""
        wf = svc.get_workflow("unknown/department", "LOW")
        assert wf.name == "default"
        approvers = svc.get_required_approvers("unknown/department", "MEDIUM")
        assert approvers == ["domain_owner"]

    def test_list_workflows_returns_all(self, svc: ApprovalWorkflowService) -> None:
        """list_workflows should return all default workflows."""
        workflows = svc.list_workflows()
        assert len(workflows) == 8
        names = [w.name for w in workflows]
        assert "engineering_standard" in names
        assert "legal_standard" in names
        assert "default" in names

    def test_no_auto_approve_for_legal(self, svc: ApprovalWorkflowService) -> None:
        """Legal workflows have no auto_approve_below, so never auto-approve."""
        assert svc.check_auto_approve("legal/ip", "LOW") is False

    def test_finance_low_single_approver(self, svc: ApprovalWorkflowService) -> None:
        """Finance LOW severity needs only finance_controller."""
        approvers = svc.get_required_approvers("finance/budgets", "LOW")
        assert approvers == ["finance_controller"]
