"""Consensus voting for CRITICAL severity rules.

Per CLAUDE.md §15.2 (Tier 1.4): when a CRITICAL-severity rule receives a DENY
verdict, a second independent LLM evaluation is triggered. If both calls agree,
the original verdict stands. If they disagree, the verdict becomes
NEEDS_CONFIRMATION with a consensus_disagreement flag.

This ensures high-stakes denials are double-checked before enforcement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ConsensusResult:
    """Result of consensus voting on a rule verdict.

    Attributes:
        final_verdict: The verdict after consensus evaluation.
        reasoning: Combined reasoning from both evaluations.
        consensus_agreed: True if both evaluations produced the same verdict.
        first_verdict: The verdict from the initial evaluation.
        second_verdict: The verdict from the second (consensus) evaluation,
            or None if consensus was not required.
    """

    final_verdict: str
    reasoning: str
    consensus_agreed: bool
    first_verdict: str
    second_verdict: str | None


async def check_consensus(
    *,
    rule: dict[str, Any],
    first_verdict: str,
    first_reasoning: str,
    evaluate_fn: Callable[..., Any],
    context: dict[str, Any],
) -> ConsensusResult:
    """Check consensus for a rule verdict via a second independent evaluation.

    Consensus is only triggered when ALL of:
      - rule severity is CRITICAL
      - first_verdict is DENY

    For all other cases, the original verdict is returned as-is.

    Args:
        rule: Rule dict, must include a ``severity`` key.
        first_verdict: The verdict string from the initial evaluation.
        first_reasoning: The reasoning from the initial evaluation.
        evaluate_fn: An async callable that performs an independent evaluation.
            Called with ``(rule=rule, context=context)`` and must return a dict
            with at least ``verdict`` and ``reasoning`` keys.
        context: The evaluation context dict forwarded to *evaluate_fn*.

    Returns:
        A ``ConsensusResult`` describing the outcome.
    """
    severity = str(rule.get("severity", "")).upper()
    verdict_upper = first_verdict.upper()

    if severity != "CRITICAL" or verdict_upper != "DENY":
        logger.debug(
            "consensus_skipped",
            rule_id=rule.get("id"),
            severity=severity,
            verdict=verdict_upper,
        )
        return ConsensusResult(
            final_verdict=first_verdict,
            reasoning=first_reasoning,
            consensus_agreed=True,
            first_verdict=first_verdict,
            second_verdict=None,
        )

    logger.info(
        "consensus_triggered",
        rule_id=rule.get("id"),
        severity=severity,
        first_verdict=verdict_upper,
    )

    second_result = await evaluate_fn(rule=rule, context=context)
    second_verdict = str(second_result.get("verdict", "")).upper()
    second_reasoning = str(second_result.get("reasoning", ""))

    if verdict_upper == second_verdict:
        logger.info(
            "consensus_agreed",
            rule_id=rule.get("id"),
            verdict=verdict_upper,
        )
        return ConsensusResult(
            final_verdict=first_verdict,
            reasoning=first_reasoning,
            consensus_agreed=True,
            first_verdict=first_verdict,
            second_verdict=second_result.get("verdict", second_verdict),
        )

    logger.warning(
        "consensus_disagreed",
        rule_id=rule.get("id"),
        first_verdict=verdict_upper,
        second_verdict=second_verdict,
    )
    combined_reasoning = (
        f"Consensus disagreement: first evaluation returned {first_verdict} "
        f"({first_reasoning}), second evaluation returned "
        f"{second_result.get('verdict', second_verdict)} ({second_reasoning}). "
        f"Escalating to NEEDS_CONFIRMATION."
    )
    return ConsensusResult(
        final_verdict="NEEDS_CONFIRMATION",
        reasoning=combined_reasoning,
        consensus_agreed=False,
        first_verdict=first_verdict,
        second_verdict=second_result.get("verdict", second_verdict),
    )
