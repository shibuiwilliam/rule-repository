"""Cost tracking for LLM API usage.

Tracks token consumption and estimated costs per evaluation.
Cost records are logged via structlog for aggregation and
analysis. A future migration will add cost columns directly
to the evaluations table.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Pricing table: model_id -> (input_cost_per_1k_tokens, output_cost_per_1k_tokens)
# Prices in USD. Updated as of 2025. These are estimates and should
# be kept in sync with actual provider pricing.
_PRICING_TABLE: dict[str, tuple[float, float]] = {
    # Gemini models
    "gemini-3-flash-preview": (0.00001, 0.00004),
    "gemini-3.1-pro-preview": (0.00025, 0.001),
    "gemini-3.1-flash-lite-preview": (0.000005, 0.00002),
    # Anthropic models (placeholder)
    "claude-sonnet-4-20250514": (0.003, 0.015),
    "claude-haiku-3-5-20241022": (0.0008, 0.004),
    # OpenAI models (placeholder)
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
}

# Fallback pricing for unknown models
_DEFAULT_INPUT_COST_PER_1K = 0.0001
_DEFAULT_OUTPUT_COST_PER_1K = 0.0004


@dataclass(frozen=True)
class CostRecord:
    """Record of token usage and estimated cost for an LLM call.

    Attributes:
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        model_id: The model identifier used for the call.
        estimated_cost_usd: Estimated cost in US dollars.
    """

    input_tokens: int
    output_tokens: int
    model_id: str
    estimated_cost_usd: float


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of an LLM call based on token usage.

    Uses a simple pricing table keyed by model ID. Falls back to
    conservative default pricing for unknown models.

    Args:
        model_id: The model identifier (e.g., "gemini-3-flash-preview").
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.

    Returns:
        Estimated cost in US dollars.
    """
    if model_id in _PRICING_TABLE:
        input_rate, output_rate = _PRICING_TABLE[model_id]
    else:
        input_rate = _DEFAULT_INPUT_COST_PER_1K
        output_rate = _DEFAULT_OUTPUT_COST_PER_1K

    cost = (input_tokens / 1000.0) * input_rate + (output_tokens / 1000.0) * output_rate
    return round(cost, 8)


def track_cost(record: CostRecord) -> None:
    """Log a cost record for aggregation and analysis.

    This function logs the cost information via structlog. In a future
    iteration, this will also persist the cost to the evaluations table
    once the cost columns are added via migration.

    Args:
        record: The cost record to track.
    """
    logger.info(
        "llm_cost_tracked",
        model_id=record.model_id,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        estimated_cost_usd=record.estimated_cost_usd,
    )
