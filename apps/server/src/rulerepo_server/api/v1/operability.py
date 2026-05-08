"""Operability API endpoints.

Provides system health, Prometheus metrics, per-tenant cost tracking,
SLO monitoring, and circuit breaker status.

Routes:
    GET /api/v1/ops/health              — full system health
    GET /api/v1/ops/metrics             — Prometheus-compatible metrics
    GET /api/v1/ops/cost/{tenant_id}    — tenant cost summary
    GET /api/v1/ops/cost/{tenant_id}/breakdown — detailed cost breakdown
    GET /api/v1/ops/slo                 — SLO status
    GET /api/v1/ops/circuit-breakers    — LLM circuit breaker status
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ops", tags=["operability"])


@router.get("/health")
async def ops_health() -> dict:
    """Full system health check.

    Probes all downstream dependencies (Postgres, Elasticsearch, Neo4j,
    Redis, LLM provider) and returns per-component status with latency.

    Returns:
        A SystemHealth dict with ``overall`` status and per-component checks.
    """
    from rulerepo_server.services.operability.health import health_service

    health = await health_service.full_health_check()
    return asdict(health)


@router.get("/metrics")
async def ops_metrics() -> PlainTextResponse:
    """Prometheus-compatible metrics endpoint.

    Returns all accumulated metrics in Prometheus text exposition format.
    This replaces the placeholder ``/metrics`` endpoint with detailed
    per-domain, per-tenant, and per-model metrics.

    Returns:
        Plain text in Prometheus exposition format.
    """
    from rulerepo_server.core.metrics import metrics_collector

    output = metrics_collector.get_prometheus_output()
    return PlainTextResponse(output, media_type="text/plain; charset=utf-8")


@router.get("/cost/{tenant_id}")
async def ops_tenant_cost(
    tenant_id: str,
    period_start: str | None = Query(
        default=None,
        description="ISO 8601 start of period (defaults to start of current month)",
    ),
    period_end: str | None = Query(
        default=None,
        description="ISO 8601 end of period (defaults to now)",
    ),
) -> dict:
    """Tenant cost summary.

    Returns aggregate cost information for a tenant over the specified
    period, including breakdowns by model and domain.

    Args:
        tenant_id: Tenant or organization identifier.
        period_start: Start of the reporting period (ISO 8601).
        period_end: End of the reporting period (ISO 8601).

    Returns:
        A TenantCostSummary dict.
    """
    from rulerepo_server.core.metrics import metrics_collector

    now = datetime.now(tz=UTC)
    if period_start:
        start = datetime.fromisoformat(period_start)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    end = datetime.fromisoformat(period_end) if period_end else now

    summary = metrics_collector.get_tenant_cost_summary(tenant_id, start, end)
    return asdict(summary)


@router.get("/cost/{tenant_id}/breakdown")
async def ops_tenant_cost_breakdown(
    tenant_id: str,
    period_start: str | None = Query(
        default=None,
        description="ISO 8601 start of period (defaults to start of current month)",
    ),
    period_end: str | None = Query(
        default=None,
        description="ISO 8601 end of period (defaults to now)",
    ),
    monthly_budget: float | None = Query(
        default=None,
        description="Monthly budget in USD for utilization calculation",
    ),
) -> dict:
    """Detailed cost breakdown for a tenant.

    Returns per-model, per-domain, and per-day cost breakdowns along
    with optional budget utilization status.

    Args:
        tenant_id: Tenant or organization identifier.
        period_start: Start of the reporting period (ISO 8601).
        period_end: End of the reporting period (ISO 8601).
        monthly_budget: Optional monthly budget for utilization check.

    Returns:
        A dict with ``breakdown`` and optionally ``budget_status``.
    """
    from rulerepo_server.services.operability.cost_tracker import cost_tracker

    now = datetime.now(tz=UTC)
    if period_start:
        start = datetime.fromisoformat(period_start)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    end = datetime.fromisoformat(period_end) if period_end else now

    breakdown = cost_tracker.get_cost_breakdown(tenant_id, start, end)
    result: dict = {"breakdown": asdict(breakdown)}

    if monthly_budget is not None:
        budget_status = cost_tracker.check_budget(tenant_id, monthly_budget)
        result["budget_status"] = asdict(budget_status)

    return result


@router.get("/slo")
async def ops_slo() -> dict:
    """SLO status.

    Returns current Service Level Objective metrics including latency
    percentiles, availability, and error rate.

    Returns:
        An SLOStatus dict with ``within_slo`` indicator.
    """
    from rulerepo_server.services.operability.health import health_service

    slo = await health_service.slo_status()
    return asdict(slo)


@router.get("/circuit-breakers")
async def ops_circuit_breakers() -> dict:
    """LLM circuit breaker status.

    Returns the current state of circuit breakers for all known LLM
    providers, including failure counts and next retry times.

    Returns:
        A dict with a ``providers`` list of CircuitBreakerStatus objects.
    """
    from rulerepo_server.services.operability.llm_fallback import llm_fallback_handler

    statuses = llm_fallback_handler.get_all_circuit_breaker_statuses()
    return {"providers": [asdict(s) for s in statuses]}
