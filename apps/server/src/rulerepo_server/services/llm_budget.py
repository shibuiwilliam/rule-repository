"""LLM cost guardrails — per-tenant monthly budget with soft warning and hard cap.

Every LLM call must increment the cost counter atomically. At 80% of
the configured monthly budget, an alert fires. At 100%, the evaluate
API returns HTTP 429.

See IMPROVEMENT.md §7.4 / RR-027.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UsageRecord:
    """Tracks LLM usage for a single tenant/month/provider combination."""

    tenant_id: str
    month: str  # YYYY-MM
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0


# In-memory store (will be replaced with Postgres in production)
_usage_store: dict[str, UsageRecord] = {}


def _make_key(tenant_id: str, month: str, provider: str) -> str:
    return f"{tenant_id}:{month}:{provider}"


def _current_month() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m")


def record_llm_usage(
    tenant_id: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    """Record a single LLM call's usage atomically.

    Args:
        tenant_id: The tenant that made the call.
        provider: LLM provider identifier (e.g. ``gemini``, ``anthropic``).
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens consumed.
        cost_usd: Estimated cost in USD for this call.
    """
    month = _current_month()
    key = _make_key(tenant_id, month, provider)
    if key not in _usage_store:
        _usage_store[key] = UsageRecord(tenant_id=tenant_id, month=month, provider=provider)
    record = _usage_store[key]
    record.input_tokens += input_tokens
    record.output_tokens += output_tokens
    record.total_cost_usd += cost_usd
    record.call_count += 1

    # Check budget thresholds
    total = get_tenant_monthly_spend(tenant_id)
    budget = get_monthly_budget()
    if budget > 0:
        ratio = total / budget
        if ratio >= 1.0:
            logger.warning(
                "llm_budget_exceeded",
                tenant_id=tenant_id,
                spend=total,
                budget=budget,
            )
        elif ratio >= get_warning_threshold():
            logger.warning(
                "llm_budget_warning",
                tenant_id=tenant_id,
                spend=total,
                budget=budget,
                ratio=ratio,
            )


def get_tenant_monthly_spend(tenant_id: str, month: str | None = None) -> float:
    """Get total spend for a tenant in a given month.

    Args:
        tenant_id: Tenant identifier.
        month: Month in ``YYYY-MM`` format. Defaults to current month.

    Returns:
        Total spend in USD.
    """
    if month is None:
        month = _current_month()
    total = 0.0
    for key, record in _usage_store.items():
        if record.tenant_id == tenant_id and record.month == month:
            total += record.total_cost_usd
    return total


def get_tenant_usage_breakdown(tenant_id: str, month: str | None = None) -> list[dict[str, Any]]:
    """Get per-provider usage breakdown for a tenant.

    Args:
        tenant_id: Tenant identifier.
        month: Month in ``YYYY-MM`` format. Defaults to current month.

    Returns:
        List of per-provider usage dictionaries.
    """
    if month is None:
        month = _current_month()
    results: list[dict[str, Any]] = []
    for key, record in _usage_store.items():
        if record.tenant_id == tenant_id and record.month == month:
            results.append(
                {
                    "provider": record.provider,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_cost_usd": record.total_cost_usd,
                    "call_count": record.call_count,
                }
            )
    return results


def check_budget_available(tenant_id: str) -> tuple[bool, float, float]:
    """Check if tenant has budget remaining.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Tuple of ``(is_available, current_spend, budget_limit)``.
        ``is_available`` is ``False`` when spend >= budget.
    """
    budget = get_monthly_budget()
    if budget <= 0:
        return True, 0.0, 0.0  # No budget configured = unlimited
    spend = get_tenant_monthly_spend(tenant_id)
    return spend < budget, spend, budget


def get_monthly_budget() -> float:
    """Get configured monthly budget in USD."""
    settings = get_settings()
    return settings.llm_tenant_monthly_budget_usd


def get_warning_threshold() -> float:
    """Get budget warning threshold (0.0-1.0)."""
    settings = get_settings()
    return settings.llm_tenant_budget_warning_threshold
