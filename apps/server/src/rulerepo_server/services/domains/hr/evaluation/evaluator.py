"""HR domain evaluator — attendance, leave, and evaluation comment compliance."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

HR_SYSTEM_PROMPT = """You are an HR compliance evaluator. You are given an HR transaction
(attendance record, leave request, or performance evaluation comment)
and a set of organizational and labor-law rules. For each rule, determine whether
the transaction complies, violates, or requires further review.

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
- Labor law compliance (overtime limits, leave entitlements, rest periods)
- Fairness and anti-discrimination (gender bias, age bias, disability bias)
- Proper documentation (certificates, approvals, evidence)
- Privacy and confidentiality of employee data
- Consistency with organizational policy (leave balance, approval workflows)
"""


class HREvaluator:
    """Evaluates HR artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate an HR artifact against the given rules.

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
                    "reasoning": "HR evaluation requires LLM analysis. Placeholder verdict.",
                }
            )

        logger.info("hr_evaluation_complete", rules_evaluated=len(rules), verdicts=len(verdicts))
        return verdicts
