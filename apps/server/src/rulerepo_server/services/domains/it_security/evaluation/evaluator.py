"""IT Security domain evaluator — IaC plan and access request evaluation."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

IT_SECURITY_SYSTEM_PROMPT = """You are an IT Security compliance evaluator. You are given an infrastructure-as-code
plan or access request and a set of security rules. For each rule, determine whether the
artifact complies, violates, or requires further review.

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
- Least privilege principle (IAM policies, access levels)
- Network exposure (public access, open security groups, 0.0.0.0/0 CIDR)
- Encryption requirements (at rest and in transit)
- Resource tagging compliance (cost center, owner, environment)
- Access review requirements (time-limited, justified, approved)
- MFA enforcement for privileged access
"""


class ITSecurityEvaluator:
    """Evaluates IT Security artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate an IT Security artifact against the given rules.

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
                    "reasoning": "IT Security evaluation requires LLM analysis. Placeholder verdict.",
                }
            )

        logger.info(
            "it_security_evaluation_complete",
            rules_evaluated=len(rules),
            verdicts=len(verdicts),
        )
        return verdicts
