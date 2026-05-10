"""Rule health scoring — compute per-rule health from metadata completeness and activity.

Per CLAUDE_ENHANCE.md §4.4: health scoring is deterministic (no LLM needed for most
dimensions). Clarity scoring uses the LLM sparingly — once per rule per cycle.

The "effectiveness" dimension replaces the old "test_coverage" and is domain-aware:
code rules use evaluation volume, legal/document rules use precision, and
transaction/event rules use override rate.
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
    "effectiveness": 15,
    "freshness": 15,
    "activity": 15,
    "owner_engagement": 10,
}

# Backward-compatible alias
DIMENSION_ALIASES = {"test_coverage": "effectiveness"}

# Default expected deny rates by modality
_DEFAULT_EXPECTED_DENY_RATE = {
    "MUST": 0.01,
    "MUST_NOT": 0.01,
    "SHOULD": 0.1,
    "SHOULD_NOT": 0.1,
    "MAY": 0.3,
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
            lambda r: bool(r.get("governance", {}).get("owner") if isinstance(r.get("governance"), dict) else False),
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


def compute_effectiveness(
    rule: dict[str, Any],
    evaluation_count_90d: int = 0,
    deny_count_90d: int = 0,
    override_count_90d: int = 0,
) -> float:
    """Compute domain-aware effectiveness score (0-100).

    Different rule domains have different evaluation patterns:
    - Code rules: high volume expected, use evaluation count (5 evals = 100).
    - Legal/document rules: low volume, measure precision (correct deny rate).
    - Transaction/event rules: medium volume, measure low override rate.
    - Generic/untyped: balanced formula.

    A new rule with no evaluations scores 50 (neutral, not penalized).
    Code rules with 0 evaluations score 0 (unchanged behavior).

    Args:
        rule: Rule data dictionary (needs applicable_subject_types, modality).
        evaluation_count_90d: Total evaluations in last 90 days.
        deny_count_90d: DENY verdicts in last 90 days.
        override_count_90d: Manual overrides of DENY in last 90 days.

    Returns:
        Effectiveness score 0-100.
    """
    subject_types = rule.get("applicable_subject_types") or []

    if "code_diff" in subject_types:
        # Code rules: high volume expected, 5+ evaluations = 100
        return min(100.0, evaluation_count_90d * 20.0) if evaluation_count_90d > 0 else 0.0

    elif any(t in subject_types for t in ("clause_set", "document")):
        # Legal/document rules: low volume, measure precision
        if evaluation_count_90d == 0:
            return 50.0  # Neutral — hasn't been tested yet

        # Effective if deny rate is close to expected
        expected = _get_expected_deny_rate(rule)
        actual_deny_rate = deny_count_90d / evaluation_count_90d
        deviation = abs(actual_deny_rate - expected)
        return min(100.0, max(0.0, (1.0 - deviation) * 100))

    elif any(t in subject_types for t in ("transaction", "event")):
        # Transaction/event rules: medium volume, measure override rate
        if evaluation_count_90d == 0:
            return 50.0  # Neutral

        # Effective if low override rate (few false positives)
        if deny_count_90d == 0:
            # Never denied — might be over-permissive but not ineffective
            return 70.0
        override_rate = override_count_90d / max(1, deny_count_90d)
        return max(0.0, 100.0 - (override_rate * 100))

    else:
        # Generic/universal rules: balanced formula
        if evaluation_count_90d == 0:
            return 50.0  # Neutral for rules not yet tested
        return min(100.0, evaluation_count_90d * 33.0)


def _get_expected_deny_rate(rule: dict[str, Any]) -> float:
    """Get the expected deny rate for a rule based on its modality.

    Args:
        rule: Rule data dictionary.

    Returns:
        Expected deny rate (0.0 - 1.0).
    """
    # Check for explicit expected_deny_rate on the rule
    explicit = rule.get("expected_deny_rate")
    if explicit is not None:
        return float(explicit)

    # Fall back to modality-based default
    modality = rule.get("modality", "MUST")
    return _DEFAULT_EXPECTED_DENY_RATE.get(modality, 0.1)


def classify_rule_status(
    rule: dict[str, Any],
    evaluation_count_90d: int = 0,
    deny_count_90d: int = 0,
    allow_count_90d: int = 0,
    override_count_90d: int = 0,
    days_active: int = 0,
) -> str | None:
    """Classify a rule's operational status for the Compliance Cockpit.

    Args:
        rule: Rule data dictionary.
        evaluation_count_90d: Total evaluations in last 90 days.
        deny_count_90d: DENY verdicts in last 90 days.
        allow_count_90d: ALLOW verdicts in last 90 days.
        override_count_90d: Manual overrides of DENY verdicts.
        days_active: Days since the rule became active.

    Returns:
        Status string or None if rule is healthy:
        - "dormant": no evaluations and active > 90 days
        - "ineffective": high override rate (>50%)
        - "over_broad": high fire rate with mostly ALLOW verdicts
    """
    # Dormant: no evaluations AND active for a while
    if evaluation_count_90d == 0 and days_active > 90:
        return "dormant"

    # Ineffective: high override rate
    if deny_count_90d > 0:
        override_rate = override_count_90d / deny_count_90d
        if override_rate > 0.5:
            return "ineffective"

    # Over-broad: fires frequently but rarely denies
    total = evaluation_count_90d
    if total >= 10 and allow_count_90d > 0:
        allow_rate = allow_count_90d / total
        if allow_rate > 0.95:
            return "over_broad"

    return None


def compute_health_score(
    rule: dict[str, Any],
    evaluation_count_90d: int = 0,
    owner_active: bool = False,
    clarity_score: float | None = None,
    deny_count_90d: int = 0,
    override_count_90d: int = 0,
) -> dict[str, Any]:
    """Compute a composite health score for a rule.

    Args:
        rule: Rule data dictionary with all fields.
        evaluation_count_90d: Number of evaluations in the last 90 days.
        owner_active: Whether the rule owner has been active recently.
        clarity_score: LLM-assessed clarity score (0-100). None falls back to rule's
            stored clarity_score, then to 50.0 default.
        deny_count_90d: Number of DENY verdicts in the last 90 days.
        override_count_90d: Number of manual overrides of DENY in last 90 days.

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

    # Effectiveness: domain-aware replacement for old "test_coverage"
    effectiveness = compute_effectiveness(
        rule,
        evaluation_count_90d=evaluation_count_90d,
        deny_count_90d=deny_count_90d,
        override_count_90d=override_count_90d,
    )

    # Owner engagement
    owner_engagement = 100.0 if owner_active else 0.0

    dimensions = {
        "completeness": completeness,
        "clarity": clarity_score,
        "effectiveness": effectiveness,
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

    result = {
        "overall_score": round(overall, 1),
        **{k: round(v, 1) for k, v in dimensions.items()},
        "issues": issues,
    }

    # Backward compatibility: include test_coverage as alias for effectiveness
    result["test_coverage"] = result["effectiveness"]

    return result
