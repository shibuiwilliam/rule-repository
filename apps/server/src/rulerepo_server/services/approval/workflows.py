"""Per-scope approval workflows — configurable approval chains.

Determines who needs to approve a rule change based on its scope,
severity, and domain. The workflow configuration is read from
config/approval_workflows.yaml or in-memory defaults.

See IMPROVEMENT.md §9.1 / RR-021.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ApprovalStep:
    """A single step in an approval workflow."""

    role: str  # e.g., "domain_owner", "legal_counsel", "ciso"
    required: bool = True  # mandatory vs optional
    timeout_hours: int = 72  # auto-escalate after this


@dataclass
class ApprovalWorkflow:
    """A complete approval workflow for a scope/severity combination."""

    name: str
    scope_pattern: str  # glob pattern matching scope paths (e.g., "legal/*", "engineering/**")
    min_severity: str = "LOW"  # minimum severity to trigger this workflow
    steps: list[ApprovalStep] = field(default_factory=list)
    auto_approve_below: str = ""  # auto-approve if severity below this
    description: str = ""


# Default workflows — loaded at startup, can be overridden by YAML config
DEFAULT_WORKFLOWS: list[ApprovalWorkflow] = [
    ApprovalWorkflow(
        name="engineering_standard",
        scope_pattern="engineering/*",
        min_severity="LOW",
        steps=[
            ApprovalStep(role="domain_owner"),
        ],
        auto_approve_below="MEDIUM",
        description="Standard engineering rule approval — auto-approve LOW",
    ),
    ApprovalWorkflow(
        name="engineering_critical",
        scope_pattern="engineering/*",
        min_severity="CRITICAL",
        steps=[
            ApprovalStep(role="domain_owner"),
            ApprovalStep(role="security_reviewer"),
        ],
        description="Critical engineering rules need security review",
    ),
    ApprovalWorkflow(
        name="legal_standard",
        scope_pattern="legal/*",
        min_severity="LOW",
        steps=[
            ApprovalStep(role="legal_counsel"),
            ApprovalStep(role="compliance_officer", required=False),
        ],
        description="All legal rules need counsel approval",
    ),
    ApprovalWorkflow(
        name="hr_standard",
        scope_pattern="hr/*",
        min_severity="LOW",
        steps=[
            ApprovalStep(role="hr_manager"),
        ],
        description="HR rules need HR manager approval",
    ),
    ApprovalWorkflow(
        name="hr_critical",
        scope_pattern="hr/*",
        min_severity="HIGH",
        steps=[
            ApprovalStep(role="hr_manager"),
            ApprovalStep(role="legal_counsel"),
        ],
        description="High/critical HR rules also need legal review",
    ),
    ApprovalWorkflow(
        name="finance_standard",
        scope_pattern="finance/*",
        min_severity="LOW",
        steps=[
            ApprovalStep(role="finance_controller"),
        ],
        description="Finance rules need controller approval",
    ),
    ApprovalWorkflow(
        name="finance_critical",
        scope_pattern="finance/*",
        min_severity="CRITICAL",
        steps=[
            ApprovalStep(role="finance_controller"),
            ApprovalStep(role="cfo"),
        ],
        description="Critical finance rules need CFO approval",
    ),
    ApprovalWorkflow(
        name="default",
        scope_pattern="*",
        min_severity="LOW",
        steps=[
            ApprovalStep(role="domain_owner"),
        ],
        description="Default fallback workflow",
    ),
]

_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


class ApprovalWorkflowService:
    """Resolves the appropriate approval workflow for a given rule."""

    def __init__(self) -> None:
        self._workflows = list(DEFAULT_WORKFLOWS)

    def get_workflow(self, scope: str, severity: str) -> ApprovalWorkflow:
        """Find the most specific workflow matching scope and severity.

        Matching priority:
        1. Most specific scope pattern
        2. Highest min_severity that's <= the rule's severity
        """
        import fnmatch

        severity_order = _SEVERITY_ORDER.get(severity, 0)

        candidates: list[tuple[int, int, ApprovalWorkflow]] = []
        for wf in self._workflows:
            if not fnmatch.fnmatch(scope, wf.scope_pattern):
                continue
            wf_severity = _SEVERITY_ORDER.get(wf.min_severity, 0)
            if wf_severity > severity_order:
                continue
            # Score: more specific pattern + higher min_severity = better match
            specificity = len(wf.scope_pattern.replace("*", ""))
            candidates.append((specificity, wf_severity, wf))

        if not candidates:
            # Return default
            return DEFAULT_WORKFLOWS[-1]

        # Sort by specificity desc, then severity desc
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return candidates[0][2]

    def check_auto_approve(self, scope: str, severity: str) -> bool:
        """Check if a rule change can be auto-approved."""
        workflow = self.get_workflow(scope, severity)
        if not workflow.auto_approve_below:
            return False
        threshold = _SEVERITY_ORDER.get(workflow.auto_approve_below, 0)
        return _SEVERITY_ORDER.get(severity, 0) < threshold

    def get_required_approvers(self, scope: str, severity: str) -> list[str]:
        """Get list of required approver roles for a rule change."""
        workflow = self.get_workflow(scope, severity)
        return [step.role for step in workflow.steps if step.required]

    def list_workflows(self) -> list[ApprovalWorkflow]:
        """Return all configured workflows."""
        return list(self._workflows)
