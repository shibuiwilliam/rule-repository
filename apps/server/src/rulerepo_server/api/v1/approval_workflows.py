"""REST API routes for per-scope approval workflows.

See IMPROVEMENT.md RR-021.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.approval.workflows import ApprovalWorkflowService

logger = get_logger(__name__)

router = APIRouter(prefix="/approval-workflows", tags=["approval-workflows"])

# ---------------------------------------------------------------------------
# Singleton service
# ---------------------------------------------------------------------------

_service: ApprovalWorkflowService | None = None


def _get_service() -> ApprovalWorkflowService:
    """Return the module-level ApprovalWorkflowService singleton."""
    global _service
    if _service is None:
        _service = ApprovalWorkflowService()
    return _service


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ApprovalStepSchema(BaseModel):
    """A single step in an approval workflow."""

    role: str
    required: bool
    timeout_hours: int


class ApprovalWorkflowSchema(BaseModel):
    """A complete approval workflow."""

    name: str
    scope_pattern: str
    min_severity: str
    steps: list[ApprovalStepSchema]
    auto_approve_below: str
    description: str


class ResolvedWorkflowResponse(BaseModel):
    """Response for a resolved workflow lookup."""

    scope: str
    severity: str
    workflow: ApprovalWorkflowSchema
    auto_approve: bool
    required_approvers: list[str] = Field(
        description="Roles that must approve this change.",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ApprovalWorkflowSchema])
async def list_workflows(
    svc: ApprovalWorkflowService = Depends(_get_service),
) -> list[ApprovalWorkflowSchema]:
    """List all configured approval workflows."""
    workflows = svc.list_workflows()
    return [
        ApprovalWorkflowSchema(
            name=wf.name,
            scope_pattern=wf.scope_pattern,
            min_severity=wf.min_severity,
            steps=[
                ApprovalStepSchema(
                    role=step.role,
                    required=step.required,
                    timeout_hours=step.timeout_hours,
                )
                for step in wf.steps
            ],
            auto_approve_below=wf.auto_approve_below,
            description=wf.description,
        )
        for wf in workflows
    ]


@router.get("/resolve", response_model=ResolvedWorkflowResponse)
async def resolve_workflow(
    scope: str = Query(..., description="Rule scope path, e.g. 'legal/contracts'."),
    severity: str = Query(..., description="Rule severity: LOW, MEDIUM, HIGH, or CRITICAL."),
    svc: ApprovalWorkflowService = Depends(_get_service),
) -> ResolvedWorkflowResponse:
    """Resolve the approval workflow for a given scope and severity."""
    workflow = svc.get_workflow(scope, severity)
    auto_approve = svc.check_auto_approve(scope, severity)
    required_approvers = svc.get_required_approvers(scope, severity)

    return ResolvedWorkflowResponse(
        scope=scope,
        severity=severity,
        workflow=ApprovalWorkflowSchema(
            name=workflow.name,
            scope_pattern=workflow.scope_pattern,
            min_severity=workflow.min_severity,
            steps=[
                ApprovalStepSchema(
                    role=step.role,
                    required=step.required,
                    timeout_hours=step.timeout_hours,
                )
                for step in workflow.steps
            ],
            auto_approve_below=workflow.auto_approve_below,
            description=workflow.description,
        ),
        auto_approve=auto_approve,
        required_approvers=required_approvers,
    )
