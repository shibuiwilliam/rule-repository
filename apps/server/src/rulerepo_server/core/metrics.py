"""Prometheus-compatible metrics collection.

Provides an in-process ``MetricsCollector`` singleton that accumulates
counters, histograms, and gauges and renders them in the Prometheus text
exposition format. This is intentionally dependency-free (no prometheus_client
library required) so the server can always serve ``/metrics``.

Usage::

    from rulerepo_server.core.metrics import metrics_collector

    metrics_collector.record_evaluation("code_diff", "pass", 142.5, "tenant-1")
    output = metrics_collector.get_prometheus_output()
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TenantCostSummary:
    """Cost summary for a single tenant over a given period.

    Attributes:
        tenant_id: Tenant or organization identifier.
        period_start: Start of the reporting period (ISO 8601).
        period_end: End of the reporting period (ISO 8601).
        total_evaluations: Number of evaluations executed.
        total_llm_calls: Number of LLM invocations.
        total_tokens: Aggregate token count (input + output).
        estimated_cost_usd: Estimated cost in US dollars.
        breakdown_by_model: Cost broken down by model identifier.
        breakdown_by_domain: Cost broken down by business domain.
    """

    tenant_id: str
    period_start: str
    period_end: str
    total_evaluations: int
    total_llm_calls: int
    total_tokens: int
    estimated_cost_usd: float
    breakdown_by_model: dict[str, float]
    breakdown_by_domain: dict[str, float]


@dataclass
class _LLMCallRecord:
    """Internal record of a single LLM call for cost tracking."""

    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    domain: str
    tenant_id: str
    timestamp: float


class MetricsCollector:
    """Thread-safe, in-process metrics collector.

    Accumulates evaluation, LLM, and cache metrics and can render
    them as Prometheus text exposition format. Designed as a singleton
    accessed via the module-level ``metrics_collector`` instance.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # Evaluation metrics
        # key: (domain, verdict, tenant_id) -> count
        self._eval_counts: dict[tuple[str, str, str], int] = defaultdict(int)
        # key: (domain, tenant_id) -> list of latencies
        self._eval_latencies: dict[tuple[str, str], list[float]] = defaultdict(list)

        # LLM metrics
        # key: (model, tenant_id) -> count
        self._llm_call_counts: dict[tuple[str, str], int] = defaultdict(int)
        # key: (model, direction, tenant_id) -> token count
        self._llm_token_counts: dict[tuple[str, str, str], int] = defaultdict(int)
        # key: (model, tenant_id) -> cost
        self._llm_costs: dict[tuple[str, str], float] = defaultdict(float)
        # All LLM call records (for tenant cost queries)
        self._llm_records: list[_LLMCallRecord] = []

        # Cache metrics
        # key: (cache_type, hit_or_miss) -> count
        self._cache_counts: dict[tuple[str, str], int] = defaultdict(int)

        # Gauges
        self._rule_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._connector_health: dict[str, int] = {}

        # Evaluation records per tenant (for cost summary)
        self._tenant_eval_counts: dict[str, int] = defaultdict(int)

    # -----------------------------------------------------------------
    # Recording methods
    # -----------------------------------------------------------------

    def record_evaluation(
        self,
        domain: str,
        verdict: str,
        latency_ms: float,
        tenant_id: str,
    ) -> None:
        """Record a completed evaluation.

        Args:
            domain: Subject domain (e.g. ``code_diff``).
            verdict: Outcome verdict (e.g. ``pass``, ``fail``).
            latency_ms: Evaluation latency in milliseconds.
            tenant_id: Tenant identifier.
        """
        with self._lock:
            self._eval_counts[(domain, verdict, tenant_id)] += 1
            self._eval_latencies[(domain, tenant_id)].append(latency_ms)
            self._tenant_eval_counts[tenant_id] += 1

    def record_llm_call(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        latency_ms: float,
        tenant_id: str,
        domain: str = "unknown",
    ) -> None:
        """Record a single LLM call.

        Args:
            model: Model identifier.
            tokens_in: Input token count.
            tokens_out: Output token count.
            cost_usd: Estimated cost in USD.
            latency_ms: Call latency in milliseconds.
            tenant_id: Tenant identifier.
            domain: Business domain of the call.
        """
        with self._lock:
            self._llm_call_counts[(model, tenant_id)] += 1
            self._llm_token_counts[(model, "input", tenant_id)] += tokens_in
            self._llm_token_counts[(model, "output", tenant_id)] += tokens_out
            self._llm_costs[(model, tenant_id)] += cost_usd
            self._llm_records.append(
                _LLMCallRecord(
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                    domain=domain,
                    tenant_id=tenant_id,
                    timestamp=time.time(),
                )
            )

    def record_cache_event(self, hit: bool, cache_type: str) -> None:
        """Record a cache hit or miss.

        Args:
            hit: True for a cache hit, False for a miss.
            cache_type: Type of cache (e.g. ``llm_response``, ``search``).
        """
        result = "hit" if hit else "miss"
        with self._lock:
            self._cache_counts[(cache_type, result)] += 1

    def set_rule_count(self, domain: str, tenant_id: str, count: int) -> None:
        """Set the gauge for active rule count.

        Args:
            domain: Rule domain.
            tenant_id: Tenant identifier.
            count: Current number of active rules.
        """
        with self._lock:
            self._rule_counts[(domain, tenant_id)] = count

    def set_connector_health(self, connector: str, healthy: bool) -> None:
        """Set the health gauge for a connector.

        Args:
            connector: Connector name (e.g. ``postgres``, ``elasticsearch``).
            healthy: True if the connector is healthy.
        """
        with self._lock:
            self._connector_health[connector] = 1 if healthy else 0

    # -----------------------------------------------------------------
    # Output methods
    # -----------------------------------------------------------------

    def get_prometheus_output(self) -> str:
        """Render all accumulated metrics as Prometheus text exposition.

        Returns:
            A string in Prometheus text format, ready for scraping.
        """
        lines: list[str] = []

        with self._lock:
            # Evaluation counter
            lines.append("# HELP rulerepo_evaluations_total Total evaluations by domain, verdict, tenant")
            lines.append("# TYPE rulerepo_evaluations_total counter")
            for (domain, verdict, tenant_id), count in sorted(self._eval_counts.items()):
                lines.append(
                    f'rulerepo_evaluations_total{{domain="{domain}",verdict="{verdict}",'
                    f'tenant_id="{tenant_id}"}} {count}'
                )

            # Evaluation latency (simplified: sum and count for computing average)
            lines.append("# HELP rulerepo_evaluation_latency_ms Evaluation latency in milliseconds")
            lines.append("# TYPE rulerepo_evaluation_latency_ms summary")
            for (domain, tenant_id), latencies in sorted(self._eval_latencies.items()):
                if latencies:
                    sorted_lat = sorted(latencies)
                    p50 = sorted_lat[len(sorted_lat) // 2]
                    p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
                    p99_idx = min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)
                    labels = f'domain="{domain}",tenant_id="{tenant_id}"'
                    lines.append(f'rulerepo_evaluation_latency_ms{{{labels},quantile="0.5"}} {p50:.2f}')
                    lines.append(
                        f'rulerepo_evaluation_latency_ms{{{labels},quantile="0.95"}} {sorted_lat[p95_idx]:.2f}'
                    )
                    lines.append(
                        f'rulerepo_evaluation_latency_ms{{{labels},quantile="0.99"}} {sorted_lat[p99_idx]:.2f}'
                    )
                    lines.append(f"rulerepo_evaluation_latency_ms_sum{{{labels}}} {sum(latencies):.2f}")
                    lines.append(f"rulerepo_evaluation_latency_ms_count{{{labels}}} {len(latencies)}")

            # LLM call counter
            lines.append("# HELP rulerepo_llm_calls_total Total LLM calls by model and tenant")
            lines.append("# TYPE rulerepo_llm_calls_total counter")
            for (model, tenant_id), count in sorted(self._llm_call_counts.items()):
                lines.append(f'rulerepo_llm_calls_total{{model="{model}",tenant_id="{tenant_id}"}} {count}')

            # LLM token counter
            lines.append("# HELP rulerepo_llm_tokens_total Total tokens by model, direction, tenant")
            lines.append("# TYPE rulerepo_llm_tokens_total counter")
            for (model, direction, tenant_id), count in sorted(self._llm_token_counts.items()):
                lines.append(
                    f'rulerepo_llm_tokens_total{{model="{model}",direction="{direction}",'
                    f'tenant_id="{tenant_id}"}} {count}'
                )

            # LLM cost
            lines.append("# HELP rulerepo_llm_cost_usd Cumulative LLM cost in USD")
            lines.append("# TYPE rulerepo_llm_cost_usd counter")
            for (model, tenant_id), cost in sorted(self._llm_costs.items()):
                lines.append(f'rulerepo_llm_cost_usd{{model="{model}",tenant_id="{tenant_id}"}} {cost:.6f}')

            # Cache events
            lines.append("# HELP rulerepo_cache_events_total Cache hit/miss events")
            lines.append("# TYPE rulerepo_cache_events_total counter")
            for (cache_type, result), count in sorted(self._cache_counts.items()):
                lines.append(f'rulerepo_cache_events_total{{cache_type="{cache_type}",result="{result}"}} {count}')

            # Rule count gauge
            lines.append("# HELP rulerepo_rules_active Active rules by domain and tenant")
            lines.append("# TYPE rulerepo_rules_active gauge")
            for (domain, tenant_id), count in sorted(self._rule_counts.items()):
                lines.append(f'rulerepo_rules_active{{domain="{domain}",tenant_id="{tenant_id}"}} {count}')

            # Connector health gauge
            lines.append("# HELP rulerepo_connector_health Connector health (1=healthy, 0=unhealthy)")
            lines.append("# TYPE rulerepo_connector_health gauge")
            for connector, status in sorted(self._connector_health.items()):
                lines.append(f'rulerepo_connector_health{{connector="{connector}"}} {status}')

            # Server up
            lines.append("# HELP rulerepo_up Server is running")
            lines.append("# TYPE rulerepo_up gauge")
            lines.append("rulerepo_up 1")

        return "\n".join(lines) + "\n"

    def get_tenant_cost_summary(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> TenantCostSummary:
        """Compute a cost summary for a tenant over a given period.

        Args:
            tenant_id: Tenant identifier.
            period_start: Start of the reporting period.
            period_end: End of the reporting period.

        Returns:
            A populated TenantCostSummary dataclass.
        """
        start_ts = period_start.timestamp()
        end_ts = period_end.timestamp()

        total_calls = 0
        total_tokens = 0
        total_cost = 0.0
        by_model: dict[str, float] = defaultdict(float)
        by_domain: dict[str, float] = defaultdict(float)

        with self._lock:
            for rec in self._llm_records:
                if rec.tenant_id != tenant_id:
                    continue
                if rec.timestamp < start_ts or rec.timestamp > end_ts:
                    continue
                total_calls += 1
                total_tokens += rec.tokens_in + rec.tokens_out
                total_cost += rec.cost_usd
                by_model[rec.model] += rec.cost_usd
                by_domain[rec.domain] += rec.cost_usd

            total_evals = self._tenant_eval_counts.get(tenant_id, 0)

        return TenantCostSummary(
            tenant_id=tenant_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            total_evaluations=total_evals,
            total_llm_calls=total_calls,
            total_tokens=total_tokens,
            estimated_cost_usd=round(total_cost, 6),
            breakdown_by_model=dict(by_model),
            breakdown_by_domain=dict(by_domain),
        )


# Module-level singleton
metrics_collector = MetricsCollector()
