"""LLM cost and budget API endpoints (RR-027)."""

from __future__ import annotations

from fastapi import APIRouter

from rulerepo_server.services.llm_budget import (
    check_budget_available,
    get_tenant_usage_breakdown,
)

router = APIRouter(prefix="/intelligence/cost", tags=["intelligence"])


@router.get("")
async def get_cost_summary(tenant_id: str = "default") -> dict:
    """Get current month's LLM cost summary for a tenant."""
    available, spend, budget = check_budget_available(tenant_id)
    breakdown = get_tenant_usage_breakdown(tenant_id)
    return {
        "tenant_id": tenant_id,
        "current_month_spend_usd": round(spend, 4),
        "monthly_budget_usd": budget,
        "budget_remaining_usd": round(max(0, budget - spend), 4) if budget > 0 else None,
        "budget_utilization_pct": round((spend / budget) * 100, 1) if budget > 0 else None,
        "budget_available": available,
        "breakdown_by_provider": breakdown,
    }
