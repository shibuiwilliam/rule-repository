"""Per-tenant cost tracking for LLM usage and evaluations.

Maintains in-memory cost records with daily and monthly aggregation.
Supports budget monitoring with configurable thresholds.

Usage::

    from rulerepo_server.services.operability.cost_tracker import cost_tracker

    cost_tracker.record_cost("tenant-1", "gemini-3-flash-preview", 1500, 0.0012, "evaluation")
    status = cost_tracker.check_budget("tenant-1", monthly_budget=100.0)
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime


@dataclass(frozen=True)
class BudgetStatus:
    """Budget utilization status for a tenant.

    Attributes:
        budget_usd: Configured monthly budget in USD.
        spent_usd: Amount spent so far this month.
        remaining_usd: Budget remaining (may be negative if over budget).
        utilization_pct: Percentage of budget consumed.
        is_over_budget: True if spending exceeds the budget.
    """

    budget_usd: float
    spent_usd: float
    remaining_usd: float
    utilization_pct: float
    is_over_budget: bool


@dataclass(frozen=True)
class CostBreakdown:
    """Detailed cost breakdown for a tenant over a period.

    Attributes:
        by_model: Cost totals keyed by model identifier.
        by_domain: Cost totals keyed by business domain.
        by_day: Cost totals keyed by date string (YYYY-MM-DD).
        total_usd: Aggregate cost in USD.
    """

    by_model: dict[str, float]
    by_domain: dict[str, float]
    by_day: dict[str, float]
    total_usd: float


@dataclass
class _CostRecord:
    """Internal record of a single cost event."""

    tenant_id: str
    model_id: str
    tokens: int
    cost_usd: float
    domain: str
    timestamp: float
    date_key: str  # "YYYY-MM-DD"


class CostTracker:
    """Per-tenant cost tracking service.

    Thread-safe accumulator for LLM cost events with daily, monthly,
    and budget-aware queries.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[_CostRecord] = []
        # Fast lookup indices
        # (tenant_id, date_key) -> cumulative cost
        self._daily_costs: dict[tuple[str, str], float] = defaultdict(float)
        # (tenant_id, year, month) -> cumulative cost
        self._monthly_costs: dict[tuple[str, int, int], float] = defaultdict(float)

    def record_cost(
        self,
        tenant_id: str,
        model_id: str,
        tokens: int,
        cost_usd: float,
        domain: str,
    ) -> None:
        """Record a cost event.

        Args:
            tenant_id: Tenant or organization identifier.
            model_id: LLM model identifier.
            tokens: Total tokens (input + output).
            cost_usd: Estimated cost in US dollars.
            domain: Business domain of the call.
        """
        now = time.time()
        dt = datetime.fromtimestamp(now, tz=UTC)
        date_key = dt.strftime("%Y-%m-%d")

        record = _CostRecord(
            tenant_id=tenant_id,
            model_id=model_id,
            tokens=tokens,
            cost_usd=cost_usd,
            domain=domain,
            timestamp=now,
            date_key=date_key,
        )

        with self._lock:
            self._records.append(record)
            self._daily_costs[(tenant_id, date_key)] += cost_usd
            self._monthly_costs[(tenant_id, dt.year, dt.month)] += cost_usd

    def get_daily_cost(self, tenant_id: str, day: date) -> float:
        """Return total cost for a tenant on a specific date.

        Args:
            tenant_id: Tenant identifier.
            day: The date to query.

        Returns:
            Total cost in USD for that day, or 0.0 if no records exist.
        """
        date_key = day.strftime("%Y-%m-%d")
        with self._lock:
            return self._daily_costs.get((tenant_id, date_key), 0.0)

    def get_monthly_cost(self, tenant_id: str, year: int, month: int) -> float:
        """Return total cost for a tenant in a specific month.

        Args:
            tenant_id: Tenant identifier.
            year: Calendar year.
            month: Calendar month (1-12).

        Returns:
            Total cost in USD for that month, or 0.0 if no records exist.
        """
        with self._lock:
            return self._monthly_costs.get((tenant_id, year, month), 0.0)

    def check_budget(self, tenant_id: str, monthly_budget: float) -> BudgetStatus:
        """Check budget utilization for the current month.

        Args:
            tenant_id: Tenant identifier.
            monthly_budget: Monthly budget limit in USD.

        Returns:
            A BudgetStatus with current utilization details.
        """
        now = datetime.now(tz=UTC)
        spent = self.get_monthly_cost(tenant_id, now.year, now.month)
        remaining = monthly_budget - spent
        utilization = (spent / monthly_budget * 100) if monthly_budget > 0 else 0.0

        return BudgetStatus(
            budget_usd=monthly_budget,
            spent_usd=round(spent, 6),
            remaining_usd=round(remaining, 6),
            utilization_pct=round(utilization, 2),
            is_over_budget=spent > monthly_budget,
        )

    def get_cost_breakdown(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> CostBreakdown:
        """Return a detailed cost breakdown for a tenant over a period.

        Args:
            tenant_id: Tenant identifier.
            period_start: Start of the reporting period (inclusive).
            period_end: End of the reporting period (inclusive).

        Returns:
            A CostBreakdown with per-model, per-domain, and per-day totals.
        """
        start_ts = period_start.timestamp()
        end_ts = period_end.timestamp()

        by_model: dict[str, float] = defaultdict(float)
        by_domain: dict[str, float] = defaultdict(float)
        by_day: dict[str, float] = defaultdict(float)
        total = 0.0

        with self._lock:
            for rec in self._records:
                if rec.tenant_id != tenant_id:
                    continue
                if rec.timestamp < start_ts or rec.timestamp > end_ts:
                    continue
                by_model[rec.model_id] += rec.cost_usd
                by_domain[rec.domain] += rec.cost_usd
                by_day[rec.date_key] += rec.cost_usd
                total += rec.cost_usd

        return CostBreakdown(
            by_model=dict(by_model),
            by_domain=dict(by_domain),
            by_day=dict(by_day),
            total_usd=round(total, 6),
        )


# Module-level singleton
cost_tracker = CostTracker()
