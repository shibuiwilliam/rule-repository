"""Governance domain evaluator — disclosure and board minute evaluation."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

GOVERNANCE_SYSTEM_PROMPT = """You are a corporate governance compliance evaluator. You are given
a governance artifact (disclosure document or board minute) and a set of compliance rules.
For each rule, determine whether the artifact complies, violates, or requires further review.

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
- Disclosure completeness (required sections: risk factors, MD&A, financial statements)
- Board governance compliance (quorum requirements, conflict of interest declarations)
- Regulatory filing timeliness (SEC deadlines, exchange requirements)
- ESG reporting standards (GRI, SASB, TCFD framework compliance)
- Material information disclosure requirements
- Director independence requirements and voting procedures
"""


class GovernanceEvaluator:
    """Evaluates governance artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate a governance artifact against the given rules.

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
                    "reasoning": "Governance evaluation requires LLM analysis. Placeholder verdict.",
                }
            )

        logger.info(
            "governance_evaluation_complete",
            rules_evaluated=len(rules),
            verdicts=len(verdicts),
        )
        return verdicts
