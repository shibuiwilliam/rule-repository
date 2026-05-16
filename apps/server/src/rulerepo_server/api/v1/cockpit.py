"""REST API router for the Compliance Cockpit.

See PROJECT.md §6.10 and CLAUDE.md §14.10.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance-cockpit"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class DepartmentTrendResponse(BaseModel):
    """Deny-rate trend for a department."""

    department: str
    evaluation_count: int = 0
    deny_count: int = 0
    deny_rate: float = 0.0
    sparkline: list[float] = Field(default_factory=list)


class PolicyMetricResponse(BaseModel):
    """Fire/deny rates for a policy group."""

    policy_group: str
    fire_count: int = 0
    deny_count: int = 0
    fire_rate: float = 0.0
    deny_rate: float = 0.0


class AuditSummaryResponse(BaseModel):
    """Audit activity summary."""

    window_days: int
    evaluation_count: int = 0
    denial_count: int = 0
    manual_override_count: int = 0


class CockpitDashboardResponse(BaseModel):
    """Complete compliance cockpit dashboard data."""

    department_trends: list[DepartmentTrendResponse] = Field(default_factory=list)
    policy_metrics: list[PolicyMetricResponse] = Field(default_factory=list)
    audit_summary: AuditSummaryResponse | None = None


class PropagationItemResponse(BaseModel):
    """A downstream rule needing review due to upstream change."""

    upstream_rule_id: str
    upstream_statement: str
    downstream_rule_id: str
    downstream_statement: str
    changed_at: str | None = None


class ActionItemResponse(BaseModel):
    """An item in the compliance action queue."""

    item_type: str
    resource_id: str
    description: str
    priority: str = "normal"


class EvaluationItemResponse(BaseModel):
    """A single evaluation record for the compliance evaluations list."""

    id: str
    subject_type: str = ""
    verdict: str
    confidence: float = 0.0
    rule_id: str
    rule_statement: str = ""
    issue_description: str = ""
    fix_suggestion: str | None = None
    summary: str | None = None
    created_at: str
    details: dict = Field(default_factory=dict)


class EvaluationsPageResponse(BaseModel):
    """Paginated list of evaluations."""

    items: list[EvaluationItemResponse] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _require_cockpit_enabled() -> None:
    """Raise 404 if compliance cockpit is disabled."""
    from rulerepo_server.core.feature_flags import get_feature_flags

    if not get_feature_flags().compliance_cockpit_enabled:
        raise HTTPException(status_code=404, detail="Compliance Cockpit is disabled")


@router.get("/dashboard", response_model=CockpitDashboardResponse)
async def get_dashboard(
    window_days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> CockpitDashboardResponse:
    """Get the complete compliance cockpit dashboard."""
    _require_cockpit_enabled()

    from rulerepo_server.services.compliance.cockpit import ComplianceCockpitService

    svc = ComplianceCockpitService(session)
    dashboard = await svc.get_dashboard(window_days)

    return CockpitDashboardResponse(
        department_trends=[
            DepartmentTrendResponse(
                department=t.department,
                evaluation_count=t.evaluation_count,
                deny_count=t.deny_count,
                deny_rate=t.deny_rate,
                sparkline=t.sparkline,
            )
            for t in dashboard.department_trends
        ],
        policy_metrics=[
            PolicyMetricResponse(
                policy_group=m.policy_group,
                fire_count=m.fire_count,
                deny_count=m.deny_count,
                fire_rate=m.fire_rate,
                deny_rate=m.deny_rate,
            )
            for m in dashboard.policy_metrics
        ],
        audit_summary=AuditSummaryResponse(
            window_days=dashboard.audit_summary.window_days,
            evaluation_count=dashboard.audit_summary.evaluation_count,
            denial_count=dashboard.audit_summary.denial_count,
            manual_override_count=dashboard.audit_summary.manual_override_count,
        )
        if dashboard.audit_summary
        else None,
    )


@router.get("/propagation", response_model=list[PropagationItemResponse])
async def get_propagation(
    session: AsyncSession = Depends(get_db_session),
) -> list[PropagationItemResponse]:
    """List downstream rules affected by recent upstream regulatory changes."""
    _require_cockpit_enabled()

    from rulerepo_server.services.compliance.cockpit import ComplianceCockpitService

    svc = ComplianceCockpitService(session)
    items = await svc.get_regulatory_propagation()
    return [
        PropagationItemResponse(
            upstream_rule_id=item.upstream_rule_id,
            upstream_statement=item.upstream_statement,
            downstream_rule_id=item.downstream_rule_id,
            downstream_statement=item.downstream_statement,
        )
        for item in items
    ]


@router.get("/action-queue", response_model=list[ActionItemResponse])
async def get_action_queue(
    session: AsyncSession = Depends(get_db_session),
) -> list[ActionItemResponse]:
    """Get the compliance action queue."""
    _require_cockpit_enabled()

    from rulerepo_server.services.compliance.cockpit import ComplianceCockpitService

    svc = ComplianceCockpitService(session)
    items = await svc.get_action_queue()
    return [
        ActionItemResponse(
            item_type=item.item_type,
            resource_id=item.resource_id,
            description=item.description,
            priority=item.priority,
        )
        for item in items
    ]


@router.get("/evaluations", response_model=EvaluationsPageResponse)
async def list_evaluations(
    department: str = Query(..., description="Department scope to filter evaluations"),
    verdict: str | None = Query(default=None, description="Filter by verdict (allow/deny/needs_confirmation)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationsPageResponse:
    """List evaluation records filtered by department scope.

    Used by persona dashboards (HR, Legal, Finance, etc.) to show
    recent evaluations relevant to their department.
    """
    _require_cockpit_enabled()

    from sqlalchemy import func, select

    from rulerepo_server.adapters.postgres.models import EvaluationRecordModel, RuleModel

    # Base query: join evaluations with rules to get rule statements
    query = (
        select(EvaluationRecordModel, RuleModel.statement)
        .outerjoin(RuleModel, EvaluationRecordModel.rule_id == RuleModel.id)
        .where(EvaluationRecordModel.scope.ilike(f"%{department}%"))
        .order_by(EvaluationRecordModel.created_at.desc())
    )
    count_query = (
        select(func.count())
        .select_from(EvaluationRecordModel)
        .where(EvaluationRecordModel.scope.ilike(f"%{department}%"))
    )

    if verdict:
        query = query.where(EvaluationRecordModel.verdict.ilike(verdict))
        count_query = count_query.where(EvaluationRecordModel.verdict.ilike(verdict))

    # Get total
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    rows = result.all()

    items = [
        EvaluationItemResponse(
            id=str(ev.id),
            subject_type=ev.subject_type or "",
            verdict=ev.verdict,
            confidence=ev.confidence,
            rule_id=str(ev.rule_id),
            rule_statement=stmt or "",
            issue_description=f"{ev.verdict} on rule evaluation",
            fix_suggestion=None,
            summary=None,
            created_at=ev.created_at.isoformat() if ev.created_at else "",
            details={"scope": ev.scope, "model_id": ev.model_id, "cached": ev.cached},
        )
        for ev, stmt in rows
    ]

    return EvaluationsPageResponse(items=items, total=total)
