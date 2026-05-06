"""Counterexample generator for rules.

On rule create/update, generates one minimal compliant example and one
minimal violating example. Supports heuristic mode (no LLM) and
Gemini-powered mode (future use).

Tier 2.4 — Counterexample Generator.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Modality-specific framing for violating examples.
_VIOLATING_FRAMES: dict[str, str] = {
    "MUST": "fails to perform the required action",
    "MUST_NOT": "performs the explicitly prohibited action",
    "SHOULD": "neglects the recommended practice",
    "MAY": "incorrectly assumes the optional practice is required",
    "INFO": "ignores the informational guidance",
}

_COMPLIANT_FRAMES: dict[str, str] = {
    "MUST": "correctly performs the required action",
    "MUST_NOT": "correctly avoids the prohibited action",
    "SHOULD": "follows the recommended practice",
    "MAY": "optionally follows the permitted practice",
    "INFO": "acknowledges the informational guidance",
}


async def generate_counterexamples(
    rule: dict[str, Any],
    gemini_client: Any | None = None,
) -> dict[str, Any]:
    """Generate one compliant and one violating example for a rule.

    Args:
        rule: A rule dict with at least ``statement``, ``modality``, and
            ``severity`` keys.
        gemini_client: Optional Gemini client for LLM-powered generation.
            When ``None``, heuristic examples are produced instead.

    Returns:
        A dict with ``compliant``, ``violating``, and ``rule_id`` keys.
    """
    statement = rule.get("statement", "")
    modality = rule.get("modality", "MUST")
    rule_id = rule.get("id", "")

    if gemini_client is not None:
        return await _generate_with_llm(rule, gemini_client)

    compliant_frame = _COMPLIANT_FRAMES.get(modality, _COMPLIANT_FRAMES["MUST"])
    violating_frame = _VIOLATING_FRAMES.get(modality, _VIOLATING_FRAMES["MUST"])

    compliant = f"Action that {compliant_frame}: {statement}"
    violating = f"Action that {violating_frame}: {statement}"

    logger.info(
        "counterexamples_generated",
        rule_id=str(rule_id),
        mode="heuristic",
    )

    return {
        "compliant": compliant,
        "violating": violating,
        "rule_id": str(rule_id),
    }


async def _generate_with_llm(
    rule: dict[str, Any],
    gemini_client: Any,
) -> dict[str, Any]:
    """Generate counterexamples using Gemini.

    This is a placeholder for future LLM-powered generation. The prompt
    and structured-output schema will live in
    ``services/playground/prompts/counterexamples.txt``.

    Args:
        rule: The rule dict.
        gemini_client: A configured Gemini client instance.

    Returns:
        A dict with ``compliant``, ``violating``, and ``rule_id`` keys.
    """
    # Future: call gemini_client.models.generate_content with a structured
    # output schema requesting compliant and violating examples.
    # For now, fall back to heuristic generation.
    statement = rule.get("statement", "")
    modality = rule.get("modality", "MUST")
    rule_id = rule.get("id", "")

    compliant_frame = _COMPLIANT_FRAMES.get(modality, _COMPLIANT_FRAMES["MUST"])
    violating_frame = _VIOLATING_FRAMES.get(modality, _VIOLATING_FRAMES["MUST"])

    logger.info(
        "counterexamples_generated",
        rule_id=str(rule_id),
        mode="llm_placeholder",
    )

    return {
        "compliant": f"Action that {compliant_frame}: {statement}",
        "violating": f"Action that {violating_frame}: {statement}",
        "rule_id": str(rule_id),
    }
