"""REST API routes for Rule Intelligence & Observability."""

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
