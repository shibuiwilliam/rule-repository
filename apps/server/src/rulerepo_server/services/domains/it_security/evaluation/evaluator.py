"""IT Security domain evaluator — IaC plan and access request evaluation."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class ITSecurityEvaluator(BaseDomainEvaluator):
    """Evaluates IT Security artifacts against rules via LLM."""

    domain_name = "it_security"
    system_prompt = IT_SECURITY_SYSTEM_PROMPT
