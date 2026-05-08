"""Sales domain evaluator — ad copy, discount, and quote evaluation."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

SALES_SYSTEM_PROMPT = """\
You are a sales compliance evaluator. You are given a sales artifact
(ad copy, discount request, or quote) and a set of compliance rules.
For each rule, determine whether the artifact complies, violates,
or requires further review.

Respond in JSON format with a list of verdicts:
[
  {
    "rule_id": "<id>",
    "verdict": "ALLOW" | "DENY" | "NEEDS_CONFIRMATION",
    "confidence": 0.0-1.0,
    "reasoning": "<explanation>"
  }
]

Focus on:
- Advertising compliance (FTC guidelines, Japan 景表法/薬機法/特商法)
- Unsubstantiated or misleading claims
- Required disclaimers and disclosures
- Discount authority limits and margin protection
- Quote accuracy, terms completeness, and validity periods
- Anti-competitive pricing detection
- Regulatory requirements for the ad medium (web, print, TV)
"""


class SalesEvaluator:
    """Evaluates sales artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate a sales artifact against the given rules.

        In production, this calls the LLM via the router.
        Currently returns a placeholder indicating rules need human review.
        """
        if not rules:
            return []

        verdicts: list[dict[str, Any]] = []
        for rule in rules:
            verdicts.append(
                {
                    "rule_id": str(rule.get("id", "")),
                    "rule_statement": rule.get("statement", ""),
                    "verdict": "NEEDS_CONFIRMATION",
                    "confidence": 0.5,
                    "reasoning": ("Sales evaluation requires LLM analysis. Placeholder verdict."),
                }
            )

        logger.info(
            "sales_evaluation_complete",
            rules_evaluated=len(rules),
            verdicts=len(verdicts),
        )
        return verdicts
