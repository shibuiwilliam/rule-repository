"""Unit tests for Operability (workstream 7h).

Tests metrics collection, cost tracking, leader election, LLM fallback.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

# ---------------------------------------------------------------------------
# Metrics collection tests
# ---------------------------------------------------------------------------


class TestMetricsCollector:
    def test_record_evaluation(self) -> None:
        try:
            from rulerepo_server.core.metrics import MetricsCollector
        except ImportError:
            pytest.skip("Metrics collector not yet available")

        collector = MetricsCollector()
        collector.record_evaluation("engineering", "ALLOW", 150.0, "tenant_1")
        collector.record_evaluation("engineering", "DENY", 200.0, "tenant_1")
        output = collector.get_prometheus_output()
        assert "rulerepo_evaluations_total" in output

    def test_record_llm_call(self) -> None:
        try:
            from rulerepo_server.core.metrics import MetricsCollector
        except ImportError:
            pytest.skip("Metrics collector not yet available")

        collector = MetricsCollector()
        collector.record_llm_call(
            model="gemini-3-flash-preview",
            tokens_in=500,
            tokens_out=200,
            cost_usd=0.001,
            latency_ms=300.0,
            tenant_id="tenant_1",
        )
        output = collector.get_prometheus_output()
        assert "rulerepo_llm" in output

    def test_cache_event(self) -> None:
        try:
            from rulerepo_server.core.metrics import MetricsCollector
        except ImportError:
            pytest.skip("Metrics collector not yet available")

        collector = MetricsCollector()
        collector.record_cache_event(hit=True, cache_type="evaluation")
        collector.record_cache_event(hit=False, cache_type="evaluation")
        output = collector.get_prometheus_output()
        assert "cache" in output.lower()


# ---------------------------------------------------------------------------
# Cost tracker tests
# ---------------------------------------------------------------------------


class TestCostTracker:
    def test_record_and_query_cost(self) -> None:
        try:
            from rulerepo_server.services.operability.cost_tracker import CostTracker
        except ImportError:
            pytest.skip("Cost tracker not yet available")

        tracker = CostTracker()
        tracker.record_cost("tenant_1", "gemini-3-flash-preview", 1000, 0.005, "engineering")
        tracker.record_cost("tenant_1", "gemini-3-flash-preview", 500, 0.003, "hr")

        today = datetime.now(tz=UTC).date()
        daily = tracker.get_daily_cost("tenant_1", today)
        assert daily == pytest.approx(0.008, abs=0.001)

    def test_budget_check(self) -> None:
        try:
            from rulerepo_server.services.operability.cost_tracker import CostTracker
        except ImportError:
            pytest.skip("Cost tracker not yet available")

        tracker = CostTracker()
        tracker.record_cost("tenant_1", "gemini-3-flash-preview", 1000, 50.0, "engineering")
        status = tracker.check_budget("tenant_1", monthly_budget=100.0)
        assert status.spent_usd == pytest.approx(50.0)
        assert status.is_over_budget is False

    def test_over_budget(self) -> None:
        try:
            from rulerepo_server.services.operability.cost_tracker import CostTracker
        except ImportError:
            pytest.skip("Cost tracker not yet available")

        tracker = CostTracker()
        tracker.record_cost("tenant_1", "model", 1000, 150.0, "engineering")
        status = tracker.check_budget("tenant_1", monthly_budget=100.0)
        assert status.is_over_budget is True

    def test_cost_breakdown(self) -> None:
        try:
            from rulerepo_server.services.operability.cost_tracker import CostTracker
        except ImportError:
            pytest.skip("Cost tracker not yet available")

        tracker = CostTracker()
        tracker.record_cost("tenant_1", "flash", 500, 0.01, "engineering")
        tracker.record_cost("tenant_1", "pro", 500, 0.05, "legal")
        breakdown = tracker.get_cost_breakdown("tenant_1", "monthly")
        assert breakdown.total_usd == pytest.approx(0.06, abs=0.001)


# ---------------------------------------------------------------------------
# LLM fallback tests
# ---------------------------------------------------------------------------


class TestLLMFallback:
    @pytest.mark.asyncio
    async def test_fallback_on_failure_non_critical(self) -> None:
        try:
            from rulerepo_server.services.operability.llm_fallback import (
                FallbackStrategy,
                LLMFallbackHandler,
            )
        except ImportError:
            pytest.skip("LLM fallback not yet available")

        handler = LLMFallbackHandler()
        result = await handler.handle_failure(
            error=ConnectionError("timeout"),
            severity="MEDIUM",
            original_request={"diff": "..."},
        )
        assert result.strategy_used in (FallbackStrategy.CACHE_STALE, FallbackStrategy.FAIL_OPEN)

    @pytest.mark.asyncio
    async def test_fallback_on_failure_critical(self) -> None:
        try:
            from rulerepo_server.services.operability.llm_fallback import (
                FallbackStrategy,
                LLMFallbackHandler,
            )
        except ImportError:
            pytest.skip("LLM fallback not yet available")

        handler = LLMFallbackHandler()
        result = await handler.handle_failure(
            error=ConnectionError("timeout"),
            severity="CRITICAL",
            original_request={"diff": "..."},
        )
        # CRITICAL should queue for retry, not fail open
        assert result.strategy_used in (
            FallbackStrategy.QUEUE_RETRY,
            FallbackStrategy.FAIL_CLOSED,
        )

    def test_circuit_breaker_status(self) -> None:
        try:
            from rulerepo_server.services.operability.llm_fallback import LLMFallbackHandler
        except ImportError:
            pytest.skip("LLM fallback not yet available")

        handler = LLMFallbackHandler()
        status = handler.get_circuit_breaker_status("gemini")
        assert status.state in ("CLOSED", "OPEN", "HALF_OPEN")


# ---------------------------------------------------------------------------
# Leader election tests
# ---------------------------------------------------------------------------


class TestLeaderElection:
    def test_leader_election_import(self) -> None:
        try:
            from rulerepo_server.services.operability.leader_election import LeaderElection
        except ImportError:
            pytest.skip("Leader election not yet available")
        # Just verify the class exists and can be instantiated
        election = LeaderElection()
        assert election is not None


# ---------------------------------------------------------------------------
# Health service tests
# ---------------------------------------------------------------------------


class TestHealthService:
    def test_health_service_import(self) -> None:
        try:
            from rulerepo_server.services.operability.health import HealthService
        except ImportError:
            pytest.skip("Health service not yet available")
        service = HealthService()
        assert service is not None
