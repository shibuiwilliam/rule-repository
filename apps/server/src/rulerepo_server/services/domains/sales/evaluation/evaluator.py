"""Sales domain evaluator — ad copy, discount, and quote evaluation."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class SalesEvaluator(BaseDomainEvaluator):
    """Evaluates sales artifacts against rules via LLM."""

    domain_name = "sales"
    system_prompt = SALES_SYSTEM_PROMPT
