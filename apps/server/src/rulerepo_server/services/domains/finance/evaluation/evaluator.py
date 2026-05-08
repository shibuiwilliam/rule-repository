"""Finance domain evaluator — journal entry, expense, PO, and invoice evaluation."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class FinanceEvaluator(BaseDomainEvaluator):
    """Evaluates financial artifacts against rules via LLM."""

    domain_name = "finance"
    system_prompt = FINANCE_SYSTEM_PROMPT
