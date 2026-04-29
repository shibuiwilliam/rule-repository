"""REST API routes for Alerts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import AlertModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.schemas.alerts import AlertListResponse, AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _model_to_response(model: AlertModel) -> AlertResponse:
    """Convert an AlertModel ORM instance to an AlertResponse schema."""
    return AlertResponse(
        id=str(model.id),
        alert_type=model.alert_type,
        severity=model.severity,
        title=model.title,
        description=model.description,
        rule_id=str(model.rule_id) if model.rule_id else None,
        status=model.status,
        created_at=model.created_at.isoformat() if model.created_at else "",
        resolved_at=model.resolved_at.isoformat() if model.resolved_at else None,
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: str | None = Query(None, description="Filter by alert status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> AlertListResponse:
    """List alerts with optional status filter and pagination."""
    query = select(AlertModel)
    count_query = select(func.count()).select_from(AlertModel)

    if status is not None:
        query = query.where(AlertModel.status == status)
        count_query = count_query.where(AlertModel.status == status)

    # Total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    query = query.order_by(AlertModel.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    alerts = list(result.scalars().all())

    return AlertListResponse(
        items=[_model_to_response(a) for a in alerts],
        total=total,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """Fetch a single alert by ID."""
    result = await session.execute(select(AlertModel).where(AlertModel.id == UUID(alert_id)))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return _model_to_response(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """Acknowledge an alert (set status to 'acknowledged')."""
    result = await session.execute(select(AlertModel).where(AlertModel.id == UUID(alert_id)))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.status = "acknowledged"
    await session.commit()
    await session.refresh(alert)
    return _model_to_response(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """Resolve an alert (set status to 'resolved' and record resolved_at)."""
    result = await session.execute(select(AlertModel).where(AlertModel.id == UUID(alert_id)))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(tz=UTC)
    await session.commit()
    await session.refresh(alert)
    return _model_to_response(alert)
