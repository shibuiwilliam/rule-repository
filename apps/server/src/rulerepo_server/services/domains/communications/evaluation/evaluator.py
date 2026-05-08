"""Communications domain evaluator — email and chat message compliance evaluation."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class CommunicationsEvaluator(BaseDomainEvaluator):
    """Evaluates communication artifacts against rules via LLM."""

    domain_name = "communications"
    system_prompt = COMMUNICATIONS_SYSTEM_PROMPT
