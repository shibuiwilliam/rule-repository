"""Finance domain evaluator — journal entry, expense, PO, and invoice evaluation."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

FINANCE_SYSTEM_PROMPT = """You are a financial compliance evaluator. You are given a financial transaction
(journal entry, expense request, purchase order, or invoice) and a set of compliance rules.
For each rule, determine whether the transaction complies, violates, or requires further review.

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
- Segregation of duties: preparer and approver must be different individuals
- Approval thresholds: transactions above defined limits require additional authorization
- Tax compliance: correct tax registration, calculations, and withholding requirements
- Fraud indicators: round-number amounts, split transactions near thresholds, missing documentation
- Proper documentation: receipts, descriptions, justifications, competitive bids where required
- Account coding accuracy: valid chart-of-accounts entries, balanced debits and credits
"""


class FinanceEvaluator:
    """Evaluates financial artifacts against rules using domain-specific prompts."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate a financial artifact against the given rules.

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
                    "reasoning": "Finance evaluation requires LLM analysis. Placeholder verdict.",
                }
            )

        logger.info(
            "finance_evaluation_complete",
            rules_evaluated=len(rules),
            verdicts=len(verdicts),
        )
        return verdicts
