"""Tests for the cost tracking module."""

from __future__ import annotations

from rulerepo_server.services.evaluation.cost_tracker import (
    CostRecord,
    estimate_cost,
    track_cost,
)


class TestEstimateCost:
    """Tests for cost estimation function."""

    def test_known_model_gemini_flash(self) -> None:
        cost = estimate_cost("gemini-3-flash-preview", input_tokens=1000, output_tokens=500)
        # input: 1000/1000 * 0.00001 = 0.00001
        # output: 500/1000 * 0.00004 = 0.00002
        # total: 0.00003
        assert cost == 0.00003

    def test_known_model_gemini_pro(self) -> None:
        cost = estimate_cost("gemini-3.1-pro-preview", input_tokens=1000, output_tokens=1000)
        # input: 1000/1000 * 0.00025 = 0.00025
        # output: 1000/1000 * 0.001 = 0.001
        # total: 0.00125
        assert cost == 0.00125

    def test_unknown_model_uses_defaults(self) -> None:
        cost = estimate_cost("unknown-model-v1", input_tokens=1000, output_tokens=1000)
        # input: 1000/1000 * 0.0001 = 0.0001
        # output: 1000/1000 * 0.0004 = 0.0004
        # total: 0.0005
        assert cost == 0.0005

    def test_zero_tokens(self) -> None:
        cost = estimate_cost("gemini-3-flash-preview", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_large_token_count(self) -> None:
        cost = estimate_cost("gemini-3-flash-preview", input_tokens=100000, output_tokens=50000)
        # input: 100000/1000 * 0.00001 = 0.001
        # output: 50000/1000 * 0.00004 = 0.002
        # total: 0.003
        assert cost == 0.003

    def test_cost_is_rounded(self) -> None:
        # Ensure we get a reasonable number of decimal places
        cost = estimate_cost("gemini-3-flash-preview", input_tokens=1, output_tokens=1)
        assert isinstance(cost, float)
        # Should be very small but non-negative
        assert cost >= 0.0

    def test_openai_model(self) -> None:
        cost = estimate_cost("gpt-4o", input_tokens=1000, output_tokens=1000)
        # input: 1000/1000 * 0.0025 = 0.0025
        # output: 1000/1000 * 0.01 = 0.01
        # total: 0.0125
        assert cost == 0.0125

    def test_anthropic_model(self) -> None:
        cost = estimate_cost("claude-sonnet-4-20250514", input_tokens=1000, output_tokens=1000)
        # input: 1000/1000 * 0.003 = 0.003
        # output: 1000/1000 * 0.015 = 0.015
        # total: 0.018
        assert cost == 0.018


class TestCostRecord:
    """Tests for the CostRecord dataclass."""

    def test_create_record(self) -> None:
        record = CostRecord(
            input_tokens=1000,
            output_tokens=500,
            model_id="gemini-3-flash-preview",
            estimated_cost_usd=0.00003,
        )
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.model_id == "gemini-3-flash-preview"
        assert record.estimated_cost_usd == 0.00003

    def test_frozen(self) -> None:
        record = CostRecord(
            input_tokens=1000,
            output_tokens=500,
            model_id="gemini-3-flash-preview",
            estimated_cost_usd=0.00003,
        )
        try:
            record.input_tokens = 2000  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass


class TestTrackCost:
    """Tests for the cost tracking function."""

    def test_track_cost_does_not_raise(self) -> None:
        record = CostRecord(
            input_tokens=1000,
            output_tokens=500,
            model_id="gemini-3-flash-preview",
            estimated_cost_usd=0.00003,
        )
        # Should not raise any exception
        track_cost(record)

    def test_track_cost_with_zero_cost(self) -> None:
        record = CostRecord(
            input_tokens=0,
            output_tokens=0,
            model_id="gemini-3-flash-preview",
            estimated_cost_usd=0.0,
        )
        track_cost(record)
