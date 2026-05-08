"""Governance domain evaluator — disclosure and board minute evaluation."""

from __future__ import annotations

from rulerepo_server.services.domains._base_evaluator import BaseDomainEvaluator

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


class GovernanceEvaluator(BaseDomainEvaluator):
    """Evaluates governance artifacts against rules via LLM."""

    domain_name = "governance"
    system_prompt = GOVERNANCE_SYSTEM_PROMPT
