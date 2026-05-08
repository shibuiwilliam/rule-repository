"""HR domain evaluator — attendance, leave, and evaluation comment compliance."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class HREvaluator(BaseDomainEvaluator):
    """Evaluates HR artifacts against rules via LLM."""

    domain_name = "hr"
    system_prompt = HR_SYSTEM_PROMPT
