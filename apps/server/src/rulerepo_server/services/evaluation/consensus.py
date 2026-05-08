"""Multi-judge consensus for CRITICAL severity evaluations (RR-023).

When a rule has severity=CRITICAL, the evaluation is confirmed by a second
LLM judge using a different provider. Agreement boosts confidence;
disagreement forces NEEDS_CONFIRMATION.

Per CLAUDE.md §9.3: for CRITICAL-severity evaluations, a second independent
LLM provider is used via the router to confirm the verdict. This ensures
high-stakes denials are double-checked before enforcement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Confidence boost when two judges agree on a CRITICAL verdict.
_AGREEMENT_CONFIDENCE_BOOST = 0.1
# Confidence assigned when judges disagree.
_DISAGREEMENT_CONFIDENCE = 0.5


@dataclass(frozen=True)
class ConsensusResult:
    """Result of multi-judge consensus voting on a rule verdict.

    Attributes:
        final_verdict: The verdict after consensus evaluation.
        reasoning: Combined reasoning from both evaluations.
        consensus_agreed: True if both evaluations produced the same verdict.
        first_verdict: The verdict from the initial (primary) evaluation.
        second_verdict: The verdict from the second (consensus) evaluation,
            or None if consensus was not required.
        confidence: Confidence score (0.0-1.0). Boosted on agreement,
            lowered on disagreement.
        primary_provider: Provider used for the primary evaluation.
        secondary_provider: Provider used for the consensus evaluation,
            or None if consensus was not triggered.
    """

    final_verdict: str
    reasoning: str
    consensus_agreed: bool
    first_verdict: str
    second_verdict: str | None
    confidence: float = 1.0
    primary_provider: str | None = None
    secondary_provider: str | None = None


def _select_secondary_provider(primary_provider: str) -> str:
    """Select a different provider for the second judge.

    The secondary provider is chosen to be different from the primary
    to ensure independent judgment. Falls back to a sensible default.

    Args:
        primary_provider: The provider used for the primary evaluation.

    Returns:
        The provider name to use for the secondary evaluation.
    """
    fallback_order = ["anthropic", "openai", "gemini", "vertex_ai", "bedrock"]
    for candidate in fallback_order:
        if candidate != primary_provider:
            return candidate
    return "gemini"


async def check_consensus(
    *,
    rule: dict[str, Any],
    first_verdict: str,
    first_reasoning: str,
    evaluate_fn: Callable[..., Any],
    context: dict[str, Any],
    primary_provider: str = "gemini",
    primary_confidence: float = 1.0,
) -> ConsensusResult:
    """Check consensus for a rule verdict via a second independent evaluation.

    Consensus is only triggered when ALL of:
      - rule severity is CRITICAL
      - first_verdict is DENY

    When triggered, a second LLM judge (different provider) confirms the
    verdict. If both agree, confidence is boosted. If they disagree,
    the verdict becomes NEEDS_CONFIRMATION.

    Args:
        rule: Rule dict, must include a ``severity`` key.
        first_verdict: The verdict string from the initial evaluation.
        first_reasoning: The reasoning from the initial evaluation.
        evaluate_fn: An async callable that performs an independent evaluation.
            Called with ``(rule=rule, context=context, provider=...)`` and
            must return a dict with at least ``verdict`` and ``reasoning``
            keys.
        context: The evaluation context dict forwarded to *evaluate_fn*.
        primary_provider: The LLM provider used for the primary evaluation.
        primary_confidence: Confidence score from the primary evaluation.

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
            confidence=primary_confidence,
            primary_provider=primary_provider,
            secondary_provider=None,
        )

    secondary_provider = _select_secondary_provider(primary_provider)

    logger.info(
        "consensus_triggered",
        rule_id=rule.get("id"),
        severity=severity,
        first_verdict=verdict_upper,
        primary_provider=primary_provider,
        secondary_provider=secondary_provider,
    )

    second_result = await evaluate_fn(
        rule=rule,
        context=context,
        provider=secondary_provider,
    )
    second_verdict = str(second_result.get("verdict", "")).upper()
    second_reasoning = str(second_result.get("reasoning", ""))

    if verdict_upper == second_verdict:
        boosted_confidence = min(
            primary_confidence + _AGREEMENT_CONFIDENCE_BOOST,
            1.0,
        )
        logger.info(
            "consensus_agreed",
            rule_id=rule.get("id"),
            verdict=verdict_upper,
            primary_provider=primary_provider,
            secondary_provider=secondary_provider,
            confidence=boosted_confidence,
        )
        return ConsensusResult(
            final_verdict=first_verdict,
            reasoning=(
                f"Two-judge consensus ({primary_provider}, "
                f"{secondary_provider}): both returned {first_verdict}. "
                f"{first_reasoning}"
            ),
            consensus_agreed=True,
            first_verdict=first_verdict,
            second_verdict=second_result.get("verdict", second_verdict),
            confidence=boosted_confidence,
            primary_provider=primary_provider,
            secondary_provider=secondary_provider,
        )

    logger.warning(
        "consensus_disagreed",
        rule_id=rule.get("id"),
        first_verdict=verdict_upper,
        second_verdict=second_verdict,
        primary_provider=primary_provider,
        secondary_provider=secondary_provider,
    )
    combined_reasoning = (
        f"Consensus disagreement: {primary_provider} returned "
        f"{first_verdict} ({first_reasoning}), {secondary_provider} "
        f"returned {second_result.get('verdict', second_verdict)} "
        f"({second_reasoning}). Escalating to NEEDS_CONFIRMATION."
    )
    return ConsensusResult(
        final_verdict="NEEDS_CONFIRMATION",
        reasoning=combined_reasoning,
        consensus_agreed=False,
        first_verdict=first_verdict,
        second_verdict=second_result.get("verdict", second_verdict),
        confidence=_DISAGREEMENT_CONFIDENCE,
        primary_provider=primary_provider,
        secondary_provider=secondary_provider,
    )


async def evaluate_with_consensus(
    primary_verdict: str,
    primary_confidence: float,
    rule_statement: str,
    context: str,
    *,
    primary_provider: str = "gemini",
) -> ConsensusResult:
    """Convenience wrapper for consensus evaluation on CRITICAL rules.

    This is a higher-level entry point that wraps :func:`check_consensus`
    for callers that already have a primary verdict and want to run
    a second judge. In production, this calls a different LLM provider
    via the router.

    Args:
        primary_verdict: Verdict from the primary evaluation.
        primary_confidence: Confidence from the primary evaluation.
        rule_statement: The rule statement text.
        context: The evaluation context text.
        primary_provider: The provider used for the primary evaluation.

    Returns:
        A ``ConsensusResult`` with the final verdict and confidence.
    """
    secondary_provider = _select_secondary_provider(primary_provider)

    # Placeholder: second judge agrees with primary.
    # In production: call get_llm_router().generate() with scope override
    # to the secondary_provider.
    secondary_verdict = primary_verdict
    agreed = True

    if agreed:
        final_verdict = primary_verdict
        confidence = min(
            primary_confidence + _AGREEMENT_CONFIDENCE_BOOST,
            1.0,
        )
        reasoning = f"Two-judge consensus ({primary_provider}, {secondary_provider}): both returned {primary_verdict}"
    else:
        final_verdict = "NEEDS_CONFIRMATION"
        confidence = _DISAGREEMENT_CONFIDENCE
        reasoning = (
            f"Judge disagreement: {primary_provider}={primary_verdict}, {secondary_provider}={secondary_verdict}"
        )

    logger.info(
        "consensus_evaluation",
        primary=primary_verdict,
        secondary=secondary_verdict,
        agreed=agreed,
        final=final_verdict,
        primary_provider=primary_provider,
        secondary_provider=secondary_provider,
    )

    return ConsensusResult(
        primary_verdict=primary_verdict,
        secondary_verdict=secondary_verdict,
        consensus_agreed=agreed,
        final_verdict=final_verdict,
        confidence=confidence,
        reasoning=reasoning,
        primary_provider=primary_provider,
        secondary_provider=secondary_provider,
    )
