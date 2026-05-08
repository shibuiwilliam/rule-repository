"""Communications domain evaluator — email and chat message compliance evaluation."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

COMMUNICATIONS_SYSTEM_PROMPT = """\
You are a communications compliance evaluator. You are given an email or chat message
and a set of organizational communication rules. For each rule, determine whether
the message complies, violates, or requires further review.

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
- Confidentiality classification compliance
- External communication policy (what can be shared outside the organization)
- Tone and professionalism standards
- Required disclaimers in external emails
- Data leak prevention (M&A, unreleased products, financials)
- Social media policy compliance
- PII handling in communications
- Channel-appropriate content
"""


class CommunicationsEvaluator:
    """Evaluates communication artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate a communication artifact against the given rules.

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
                    "reasoning": ("Communications evaluation requires LLM analysis. Placeholder verdict."),
                }
            )

        logger.info(
            "communications_evaluation_complete",
            rules_evaluated=len(rules),
            verdicts=len(verdicts),
        )
        return verdicts
