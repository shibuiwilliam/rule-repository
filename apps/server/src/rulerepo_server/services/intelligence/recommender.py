"""Rule recommender — automated improvement suggestions based on usage patterns.

Per CLAUDE_ENHANCE.md §4.4: recommendations generated during health scoring.
Each recommendation is a database row. Humans decide whether to apply.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


def generate_recommendations(
    rule: dict[str, Any],
    health: dict[str, Any],
    analytics: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate improvement recommendations for a rule.

    Args:
        rule: Rule data dictionary.
        health: Health score data from health_scorer.
        analytics: Evaluation analytics data.

    Returns:
        List of recommendation dictionaries.
    """
    recommendations: list[dict[str, Any]] = []
    rule_id = str(rule.get("id", ""))

    # Retire: zero evaluations in 90+ days
    if analytics.get("total_evaluations", 0) == 0:
        recommendations.append(
            {
                "id": str(uuid4()),
                "rule_id": rule_id,
                "type": "retire",
                "title": "Consider retiring dormant rule",
                "description": (
                    "This rule has not been evaluated in the last 90 days. "
                    "It may no longer be relevant. Consider retiring it or expanding its scope."
                ),
                "priority": "medium",
                "status": "open",
            }
        )

    # Clarify: high NEEDS_CONFIRMATION rate
    nc_rate = analytics.get("needs_confirmation_rate", 0)
    if nc_rate > 0.3 and analytics.get("total_evaluations", 0) >= 5:
        recommendations.append(
            {
                "id": str(uuid4()),
                "rule_id": rule_id,
                "type": "clarify",
                "title": "Rule wording may be ambiguous",
                "description": (
                    f"This rule has a {nc_rate:.0%} NEEDS_CONFIRMATION rate, "
                    "suggesting the wording is unclear. Consider rewriting for precision."
                ),
                "priority": "high",
                "status": "open",
            }
        )

    # Escalate: high deny rate
    deny_rate = analytics.get("deny_rate", 0)
    if deny_rate > 0.5 and analytics.get("total_evaluations", 0) >= 10:
        recommendations.append(
            {
                "id": str(uuid4()),
                "rule_id": rule_id,
                "type": "escalate",
                "title": "Persistent non-compliance detected",
                "description": (
                    f"This rule has a {deny_rate:.0%} deny rate over the last period. "
                    "Either the organization is systematically non-compliant or the rule "
                    "is too strict. Escalate to the rule owner."
                ),
                "priority": "critical",
                "status": "open",
            }
        )

    # Strengthen: 100% allow rate with SHOULD modality
    allow_rate = analytics.get("allow_rate", 0)
    if (
        allow_rate == 1.0
        and analytics.get("total_evaluations", 0) >= 10
        and rule.get("modality") == "SHOULD"
    ):
        recommendations.append(
            {
                "id": str(uuid4()),
                "rule_id": rule_id,
                "type": "strengthen",
                "title": "Consider upgrading SHOULD to MUST",
                "description": (
                    "This rule has a 100% compliance rate. Since everyone follows it, "
                    "consider upgrading from SHOULD to MUST to make it enforceable."
                ),
                "priority": "low",
                "status": "open",
            }
        )

    # Completeness: low completeness score
    if health.get("completeness", 100) < 60:
        recommendations.append(
            {
                "id": str(uuid4()),
                "rule_id": rule_id,
                "type": "clarify",
                "title": "Incomplete rule metadata",
                "description": (
                    "This rule is missing important metadata fields. "
                    "Add rationale, scope, tags, and source references to improve discoverability."
                ),
                "priority": "medium",
                "status": "open",
            }
        )

    return recommendations
