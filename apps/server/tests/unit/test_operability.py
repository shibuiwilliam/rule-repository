"""Unit tests for Operability (workstream 7h).

Tests cost tracking, leader election, LLM fallback.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
        now = datetime.now(tz=UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = now
        breakdown = tracker.get_cost_breakdown("tenant_1", period_start, period_end)
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
        assert result.strategy_used in (
            FallbackStrategy.CACHE_STALE,
            FallbackStrategy.FAIL_OPEN,
            FallbackStrategy.QUEUE_RETRY,
        )

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
            from rulerepo_server.services.operability.llm_fallback import CircuitState, LLMFallbackHandler
        except ImportError:
            pytest.skip("LLM fallback not yet available")

        handler = LLMFallbackHandler()
        status = handler.get_circuit_breaker_status("gemini")
        assert status.state in (CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN)


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
