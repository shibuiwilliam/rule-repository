"""Rule health scoring — compute per-rule health from metadata completeness and activity.

Per CLAUDE_ENHANCE.md §4.4: health scoring is deterministic (no LLM needed for most
dimensions). Clarity scoring uses the LLM sparingly — once per rule per cycle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Weights per dimension (must sum to 100)
WEIGHTS = {
    "completeness": 20,
    "clarity": 25,
    "test_coverage": 15,
    "freshness": 15,
    "activity": 15,
    "owner_engagement": 10,
}


def compute_completeness(rule: dict[str, Any]) -> tuple[float, list[str]]:
    """Score 0-100 based on metadata field population.

    Args:
        rule: Rule data dictionary.

    Returns:
        Tuple of (score, list of issues found).
    """
    fields = {
        "statement": (20, lambda r: bool(r.get("statement") and len(str(r["statement"])) > 20)),
        "rationale": (20, lambda r: bool(r.get("rationale"))),
        "scope": (15, lambda r: bool(r.get("scope"))),
        "modality": (10, lambda r: bool(r.get("modality"))),
        "tags": (10, lambda r: bool(r.get("tags"))),
        "source_refs": (15, lambda r: bool(r.get("source_refs"))),
        "governance_owner": (
            10,
            lambda r: bool(
                r.get("governance", {}).get("owner")
                if isinstance(r.get("governance"), dict)
                else False
            ),
        ),
    }

    score = 0.0
    issues: list[str] = []
    for field_name, (weight, check) in fields.items():
        if check(rule):
            score += weight
        else:
            issues.append(f"Missing or incomplete: {field_name}")

    return score, issues


def compute_freshness(rule: dict[str, Any], now: datetime | None = None) -> float:
    """Score 0-100 based on how recently the rule was updated.

    Rules updated in the last 30 days get 100. Score decays linearly to 0 at 365 days.

    Args:
        rule: Rule data dictionary.
        now: Current time (for testing).

    Returns:
        Freshness score 0-100.
    """
    now = now or datetime.now(tz=UTC)
    updated_at = rule.get("updated_at")
    if not updated_at:
        return 0.0

    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at)
        except (ValueError, TypeError):
            return 0.0

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)

    days_since = (now - updated_at).days
    if days_since <= 30:
        return 100.0
    if days_since >= 365:
        return 0.0
    return round(100 * (1 - (days_since - 30) / 335), 1)


def compute_health_score(
    rule: dict[str, Any],
    evaluation_count_90d: int = 0,
    owner_active: bool = False,
    clarity_score: float | None = None,
) -> dict[str, Any]:
    """Compute a composite health score for a rule.

    Args:
        rule: Rule data dictionary with all fields.
        evaluation_count_90d: Number of evaluations in the last 90 days.
        owner_active: Whether the rule owner has been active recently.
        clarity_score: LLM-assessed clarity score (0-100). None falls back to rule's
            stored clarity_score, then to 50.0 default.

    Returns:
        Dictionary with overall_score, per-dimension scores, and issues.
    """
    completeness, issues = compute_completeness(rule)
    freshness = compute_freshness(rule)

    # Activity: has the rule been evaluated recently?
    activity = min(100.0, evaluation_count_90d * 10.0)  # 10+ evals = 100

    # Clarity: use provided score, fall back to stored score on rule, then default 50
    if clarity_score is None:
        clarity_score = rule.get("clarity_score") or 50.0

    # Test coverage: based on evaluation count (rules with evals have some "test" coverage)
    test_coverage = min(100.0, evaluation_count_90d * 20.0) if evaluation_count_90d > 0 else 0.0

    # Owner engagement
    owner_engagement = 100.0 if owner_active else 0.0

    dimensions = {
        "completeness": completeness,
        "clarity": clarity_score,
        "test_coverage": test_coverage,
        "freshness": freshness,
        "activity": activity,
        "owner_engagement": owner_engagement,
    }

    overall = sum(dimensions[k] * WEIGHTS[k] / 100 for k in WEIGHTS)

    if activity == 0:
        issues.append("Rule has not been evaluated in the last 90 days (dormant)")
    if not owner_active:
        issues.append("Rule owner has not been active recently")
    if freshness < 30:
        issues.append("Rule has not been updated in over 6 months")

    return {
        "overall_score": round(overall, 1),
        **{k: round(v, 1) for k, v in dimensions.items()},
        "issues": issues,
    }
