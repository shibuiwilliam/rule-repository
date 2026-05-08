"""Legal domain evaluator — contract clause and document evaluation."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

LEGAL_SYSTEM_PROMPT = """You are a legal compliance evaluator. You are given a contract clause or document
and a set of compliance rules. For each rule, determine whether the clause/document
complies, violates, or requires further review.

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
- Liability and indemnification limits
- Compliance with jurisdictional requirements
- Missing required clauses
- Non-standard or unusual terms
- Data protection and privacy compliance
"""


class LegalEvaluator:
    """Evaluates legal artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate a legal artifact against the given rules.

        In production, this calls the LLM via the router.
        Currently returns a placeholder indicating rules need human review.
        """
        if not rules:
            return []

        verdicts = []
        for rule in rules:
            verdicts.append(
                {
                    "rule_id": str(rule.get("id", "")),
                    "rule_statement": rule.get("statement", ""),
                    "verdict": "NEEDS_CONFIRMATION",
                    "confidence": 0.5,
                    "reasoning": "Legal evaluation requires LLM analysis. Placeholder verdict.",
                }
            )

        logger.info("legal_evaluation_complete", rules_evaluated=len(rules), verdicts=len(verdicts))
        return verdicts
