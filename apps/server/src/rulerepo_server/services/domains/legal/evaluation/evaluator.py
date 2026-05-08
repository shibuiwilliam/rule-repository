"""Legal domain evaluator — contract clause and document evaluation."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class LegalEvaluator(BaseDomainEvaluator):
    """Evaluates legal artifacts against rules via LLM."""

    domain_name = "legal"
    system_prompt = LEGAL_SYSTEM_PROMPT
