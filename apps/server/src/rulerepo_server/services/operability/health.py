"""Comprehensive health check service.

Provides deep health checks for all downstream dependencies (Postgres,
Elasticsearch, Neo4j, Redis, LLM providers) and SLO tracking.

Usage::

    from rulerepo_server.services.operability.health import health_service

    health = await health_service.full_health_check()
    slo = await health_service.slo_status()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ComponentHealth:
    """Health status of a single infrastructure component.

    Attributes:
        status: Current status (``healthy``, ``degraded``, ``unhealthy``).
        latency_ms: Probe latency in milliseconds, or None if the check failed.
        error: Error message if unhealthy, or None.
        last_success_at: ISO timestamp of the last successful check.
    """

    status: str
    latency_ms: float | None
    error: str | None
    last_success_at: str | None


@dataclass(frozen=True)
class SystemHealth:
    """Aggregate health of the entire system.

    Attributes:
        overall: System-wide status: ``healthy``, ``degraded``, or ``unhealthy``.
        checks: Per-component health results.
        timestamp: ISO timestamp of the health check.
    """

    overall: str
    checks: dict[str, ComponentHealth]
    timestamp: str


@dataclass(frozen=True)
class SLOStatus:
    """Service Level Objective status.

    Attributes:
        p95_latency_ms: 95th percentile evaluation latency.
        p99_latency_ms: 99th percentile evaluation latency.
        availability_pct: Percentage of successful health checks over
            the observation window.
        error_rate_pct: Percentage of failed evaluations.
        within_slo: True if all SLO targets are met.
    """

    p95_latency_ms: float
    p99_latency_ms: float
    availability_pct: float
    error_rate_pct: float
    within_slo: bool


class HealthService:
    """Orchestrates deep health checks and SLO monitoring.

    Tracks historical latencies and availability to compute SLO
    metrics over a rolling window.
    """

    # SLO targets (configurable per deployment)
    SLO_P95_LATENCY_MS = 2000.0
    SLO_P99_LATENCY_MS = 5000.0
    SLO_AVAILABILITY_PCT = 99.5
    SLO_ERROR_RATE_PCT = 1.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Rolling window of evaluation latencies for SLO computation
        self._latencies: list[float] = []
        # Rolling counters
        self._total_checks: int = 0
        self._successful_checks: int = 0
        self._total_evaluations: int = 0
        self._failed_evaluations: int = 0
        # Per-component last success
        self._last_success: dict[str, str] = {}

    def record_evaluation_latency(self, latency_ms: float, success: bool = True) -> None:
        """Record an evaluation latency sample for SLO tracking.

        Args:
            latency_ms: Evaluation latency in milliseconds.
            success: Whether the evaluation succeeded.
        """
        with self._lock:
            self._latencies.append(latency_ms)
            # Keep a bounded window (last 10000 samples)
            if len(self._latencies) > 10000:
                self._latencies = self._latencies[-10000:]
            self._total_evaluations += 1
            if not success:
                self._failed_evaluations += 1

    async def _check_postgres(self) -> ComponentHealth:
        """Probe PostgreSQL connectivity."""
        start = time.monotonic()
        try:
            from rulerepo_server.adapters.postgres.session import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            latency = (time.monotonic() - start) * 1000
            now = datetime.now(tz=UTC).isoformat()
            with self._lock:
                self._last_success["postgres"] = now
            return ComponentHealth(status="healthy", latency_ms=round(latency, 2), error=None, last_success_at=now)
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                status="unhealthy",
                latency_ms=round(latency, 2),
                error=str(exc),
                last_success_at=self._last_success.get("postgres"),
            )

    async def _check_elasticsearch(self) -> ComponentHealth:
        """Probe Elasticsearch connectivity."""
        start = time.monotonic()
        try:
            from rulerepo_server.adapters.elasticsearch.client import get_es_client

            es = get_es_client()
            await es.info()
            latency = (time.monotonic() - start) * 1000
            now = datetime.now(tz=UTC).isoformat()
            with self._lock:
                self._last_success["elasticsearch"] = now
            return ComponentHealth(status="healthy", latency_ms=round(latency, 2), error=None, last_success_at=now)
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                status="unhealthy",
                latency_ms=round(latency, 2),
                error=str(exc),
                last_success_at=self._last_success.get("elasticsearch"),
            )

    async def _check_neo4j(self) -> ComponentHealth:
        """Probe Neo4j connectivity."""
        start = time.monotonic()
        try:
            from rulerepo_server.adapters.neo4j.client import get_neo4j_driver

            driver = get_neo4j_driver()
            await driver.verify_connectivity()
            latency = (time.monotonic() - start) * 1000
            now = datetime.now(tz=UTC).isoformat()
            with self._lock:
                self._last_success["neo4j"] = now
            return ComponentHealth(status="healthy", latency_ms=round(latency, 2), error=None, last_success_at=now)
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                status="unhealthy",
                latency_ms=round(latency, 2),
                error=str(exc),
                last_success_at=self._last_success.get("neo4j"),
            )

    async def _check_redis(self) -> ComponentHealth:
        """Probe Redis connectivity."""
        start = time.monotonic()
        try:
            import redis.asyncio as aioredis

            from rulerepo_server.core.config import get_settings

            settings = get_settings()
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            try:
                await r.ping()
            finally:
                await r.aclose()
            latency = (time.monotonic() - start) * 1000
            now = datetime.now(tz=UTC).isoformat()
            with self._lock:
                self._last_success["redis"] = now
            return ComponentHealth(status="healthy", latency_ms=round(latency, 2), error=None, last_success_at=now)
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                status="unhealthy",
                latency_ms=round(latency, 2),
                error=str(exc),
                last_success_at=self._last_success.get("redis"),
            )

    async def _check_llm_provider(self) -> ComponentHealth:
        """Probe LLM provider availability via circuit breaker status.

        Does not make an actual LLM call; instead checks the circuit
        breaker state to determine availability.
        """
        start = time.monotonic()
        try:
            from rulerepo_server.services.operability.llm_fallback import llm_fallback_handler

            available = llm_fallback_handler.is_provider_available("gemini")
            latency = (time.monotonic() - start) * 1000

            if available:
                now = datetime.now(tz=UTC).isoformat()
                with self._lock:
                    self._last_success["llm_provider"] = now
                return ComponentHealth(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    error=None,
                    last_success_at=now,
                )
            else:
                return ComponentHealth(
                    status="degraded",
                    latency_ms=round(latency, 2),
                    error="Circuit breaker is open; LLM provider temporarily unavailable",
                    last_success_at=self._last_success.get("llm_provider"),
                )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                status="unhealthy",
                latency_ms=round(latency, 2),
                error=str(exc),
                last_success_at=self._last_success.get("llm_provider"),
            )

    async def full_health_check(self) -> SystemHealth:
        """Run comprehensive health checks against all components.

        Returns:
            A SystemHealth object with per-component results and an
            aggregate status.
        """
        checks: dict[str, ComponentHealth] = {}

        # Run checks (sequential to avoid overwhelming downstream services)
        checks["postgres"] = await self._check_postgres()
        checks["elasticsearch"] = await self._check_elasticsearch()
        checks["neo4j"] = await self._check_neo4j()
        checks["redis"] = await self._check_redis()
        checks["llm_provider"] = await self._check_llm_provider()

        # Update availability counters
        with self._lock:
            self._total_checks += 1
            all_healthy = all(c.status == "healthy" for c in checks.values())
            if all_healthy:
                self._successful_checks += 1

        # Determine overall status
        statuses = [c.status for c in checks.values()]
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        from rulerepo_server.core.metrics import metrics_collector

        for name, check in checks.items():
            metrics_collector.set_connector_health(name, check.status == "healthy")

        return SystemHealth(
            overall=overall,
            checks=checks,
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    async def slo_status(self) -> SLOStatus:
        """Compute current SLO status from accumulated metrics.

        Returns:
            An SLOStatus with latency percentiles, availability,
            error rate, and whether the system is within SLO targets.
        """
        with self._lock:
            latencies = list(self._latencies)
            total_checks = self._total_checks
            successful_checks = self._successful_checks
            total_evals = self._total_evaluations
            failed_evals = self._failed_evaluations

        if latencies:
            sorted_lat = sorted(latencies)
            p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
            p99_idx = min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)
            p95 = sorted_lat[p95_idx]
            p99 = sorted_lat[p99_idx]
        else:
            p95 = 0.0
            p99 = 0.0

        availability = (successful_checks / total_checks * 100) if total_checks > 0 else 100.0
        error_rate = (failed_evals / total_evals * 100) if total_evals > 0 else 0.0

        within_slo = (
            p95 <= self.SLO_P95_LATENCY_MS
            and p99 <= self.SLO_P99_LATENCY_MS
            and availability >= self.SLO_AVAILABILITY_PCT
            and error_rate <= self.SLO_ERROR_RATE_PCT
        )

        return SLOStatus(
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            availability_pct=round(availability, 2),
            error_rate_pct=round(error_rate, 2),
            within_slo=within_slo,
        )


# Module-level singleton
health_service = HealthService()
