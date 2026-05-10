"""REST API routes for Rule Intelligence & Analytics."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.services.intelligence.service import IntelligenceService

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


async def _get_intelligence_service(
    session: AsyncSession = Depends(get_db_session),
) -> IntelligenceService:
    return IntelligenceService(session)


@router.get("/summary")
async def get_home_summary(
    project_id: str | None = Query(default=None),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """One-call summary for the outcome-oriented home dashboard.

    Returns compliance rate, trend, rule counts by status, top violated rules,
    recent corrections, and pending action counts.
    """
    return await service.get_home_summary(project_id=project_id)


@router.get("/dashboard")
async def get_dashboard(
    project_id: str | None = Query(default=None),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Corpus-wide intelligence dashboard: health summary, evaluation volume, verdicts."""
    return await service.get_dashboard(project_id=project_id)


@router.get("/health")
async def get_health_scores(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="overall_score"),
    project_id: str | None = Query(default=None),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Paginated rule health scores, sortable by dimension."""
    return await service.get_health_scores(page=page, page_size=page_size, sort_by=sort_by, project_id=project_id)


@router.get("/health/{rule_id}")
async def get_rule_health(
    rule_id: str,
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Detailed health breakdown for a single rule."""
    return await service.get_rule_health(rule_id)


@router.get("/analytics")
async def get_analytics(
    period: int = Query(default=30, ge=1, le=365, alias="period_days"),
    project_id: str | None = Query(default=None),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Corpus-wide evaluation analytics for the given period."""
    return await service.get_analytics(period_days=period, project_id=project_id)


@router.get("/analytics/{rule_id}")
async def get_rule_analytics(
    rule_id: str,
    period: int = Query(default=30, ge=1, le=365, alias="period_days"),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Per-rule evaluation analytics (fire rate, deny rate, trends)."""
    return await service.get_rule_analytics_detail(rule_id, period_days=period)


@router.get("/recommendations")
async def get_recommendations(
    status: str = Query(default="open"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    project_id: str | None = Query(default=None),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Active improvement recommendations, prioritized."""
    return await service.get_recommendations(status=status, page=page, page_size=page_size, project_id=project_id)


# ---------------------------------------------------------------------------
# Agent Performance Analytics (PROJECT_IMPROVEMENT.md §2)
# ---------------------------------------------------------------------------


@router.get("/agents")
async def list_agents(
    period: int = Query(default=30, ge=1, le=365, alias="period_days"),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """List all agents with compliance rates and evaluation counts."""
    from rulerepo_server.services.intelligence.agent_analytics import get_agent_list

    agents = await get_agent_list(service._session, period_days=period)
    return {"agents": agents, "period_days": period}


@router.get("/agents/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    period: int = Query(default=30, ge=1, le=365, alias="period_days"),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Per-agent analytics: compliance trend, top violations."""
    from rulerepo_server.services.intelligence.agent_analytics import (
        get_agent_detail as _get_detail,
    )

    return await _get_detail(service._session, agent_id, period_days=period)


# ---------------------------------------------------------------------------
# Rule Effectiveness (PROJECT_ENHANCE.md §2a)
# ---------------------------------------------------------------------------


@router.get("/effectiveness/{rule_id}")
async def get_rule_effectiveness(
    rule_id: str,
    period: int = Query(default=90, ge=1, le=365, alias="period_days"),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Per-rule effectiveness score: precision, prevention rate, agent adoption."""
    from rulerepo_server.services.intelligence.effectiveness import compute_effectiveness

    return await compute_effectiveness(service._session, rule_id, period_days=period)


# ---------------------------------------------------------------------------
# Weekly Digest (PROJECT_ENHANCE.md §2b)
# ---------------------------------------------------------------------------


@router.get("/digest")
async def get_weekly_digest(
    project_id: str | None = Query(default=None),
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Weekly governance digest with compliance trends, top violations, and pending actions."""
    from rulerepo_server.services.intelligence.digest import generate_weekly_digest

    return await generate_weekly_digest(service._session, project_id=project_id)


# ---------------------------------------------------------------------------
# Team Comparison (PROJECT_ENHANCE.md §2c)
# ---------------------------------------------------------------------------


@router.get("/comparison")
async def get_project_comparison(
    service: IntelligenceService = Depends(_get_intelligence_service),
) -> dict:
    """Compare compliance metrics across all projects."""
    from sqlalchemy import func, select

    from rulerepo_server.adapters.postgres.models import ProjectModel, RuleModel
    from rulerepo_server.services.intelligence.analytics import get_compliance_trend

    # Get all projects
    projects_result = await service._session.execute(select(ProjectModel))
    projects = projects_result.scalars().all()

    comparison: list[dict] = []
    for project in projects:
        # Rule count
        rule_count_result = await service._session.execute(
            select(func.count(RuleModel.id)).where(RuleModel.project_id == project.id)
        )
        rule_count = rule_count_result.scalar_one()

        # Compliance trend (last 7 days)
        trend = await get_compliance_trend(service._session, days=7)
        latest_rate = trend[-1]["compliance_rate"] if trend else 0.0

        comparison.append(
            {
                "project_id": str(project.id),
                "project_name": project.name,
                "rule_count": rule_count,
                "compliance_rate": latest_rate,
            }
        )

    comparison.sort(key=lambda x: x["compliance_rate"], reverse=True)
    return {"projects": comparison}
