"""Conflict-Aware Verdict Aggregator — resolves OVERRIDES, CONFLICTS_WITH, DEPENDS_ON.

Per CLAUDE_ENHANCE.md §2.3: replaces simple verdict aggregation when
relationships exist between evaluated rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import RuleVerdict, Verdict
from rulerepo_server.services.evaluation.graph_resolver import EvaluationPlan

logger = get_logger(__name__)

# Severity ordering for conflict tiebreaking
_SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
_MODALITY_ORDER = {"MUST": 4, "MUST_NOT": 4, "SHOULD": 3, "MAY": 2, "INFO": 1}


@dataclass(frozen=True)
class ConflictResolution:
    """Records how a conflict between two rules was resolved."""

    rule_a_id: str
    rule_b_id: str
    relationship: str
    winner_id: str
    reason: str
    discarded_verdict: str


def aggregate_with_conflicts(
    rule_verdicts: list[RuleVerdict],
    plan: EvaluationPlan,
    rules: dict[str, dict[str, Any]],
) -> tuple[Verdict, list[ConflictResolution]]:
    """Aggregate verdicts using relationship graph for conflict resolution.

    Per CLAUDE_ENHANCE.md §2.3:
    1. Remove overridden verdicts (OVERRIDES / REFINES)
    2. Resolve CONFLICTS_WITH pairs (severity > modality > specificity)
    3. Remove skipped-by-dependency (DEPENDS_ON with DENY prerequisite)
    4. Standard aggregation on remaining

    Args:
        rule_verdicts: Per-rule verdicts from evaluation.
        plan: EvaluationPlan from graph resolver.
        rules: Map of rule_id → rule dict for metadata access.

    Returns:
        Tuple of (overall Verdict, list of ConflictResolutions).
    """
    resolutions: list[ConflictResolution] = []
    verdict_map = {v.rule_id: v for v in rule_verdicts}
    active_ids = set(verdict_map.keys())

    # 1. Remove overridden verdicts
    for overridden_id, overriding_id in plan.overrides.items():
        if overridden_id in active_ids and overriding_id in active_ids:
            overridden_v = verdict_map.get(overridden_id)
            if overridden_v:
                resolutions.append(
                    ConflictResolution(
                        rule_a_id=overriding_id,
                        rule_b_id=overridden_id,
                        relationship="OVERRIDES",
                        winner_id=overriding_id,
                        reason=f"Rule {overriding_id[:8]} overrides {overridden_id[:8]}",
                        discarded_verdict=overridden_v.verdict.value,
                    )
                )
                active_ids.discard(overridden_id)

    # 2. Resolve CONFLICTS_WITH pairs
    for rule_a_id, rule_b_id in plan.conflicts:
        if rule_a_id in active_ids and rule_b_id in active_ids:
            winner, reason = _resolve_conflict(rule_a_id, rule_b_id, rules, verdict_map)
            loser = rule_b_id if winner == rule_a_id else rule_a_id
            loser_v = verdict_map.get(loser)
            if loser_v and winner:
                resolutions.append(
                    ConflictResolution(
                        rule_a_id=rule_a_id,
                        rule_b_id=rule_b_id,
                        relationship="CONFLICTS_WITH",
                        winner_id=winner,
                        reason=reason,
                        discarded_verdict=loser_v.verdict.value,
                    )
                )
                active_ids.discard(loser)

    # 3. Remove skipped-by-dependency
    for prereq_id, dependent_ids in plan.skip_if_denied.items():
        prereq_v = verdict_map.get(prereq_id)
        if prereq_v and prereq_v.verdict == Verdict.DENY:
            for dep_id in dependent_ids:
                if dep_id in active_ids:
                    active_ids.discard(dep_id)
                    logger.info(
                        "rule_skipped_dependency_denied",
                        rule_id=dep_id,
                        prereq_id=prereq_id,
                    )

    # 4. Standard aggregation on remaining verdicts
    remaining = [verdict_map[rid] for rid in active_ids if rid in verdict_map]

    if any(v.verdict == Verdict.DENY for v in remaining):
        overall = Verdict.DENY
    elif any(v.verdict == Verdict.NEEDS_CONFIRMATION for v in remaining):
        overall = Verdict.NEEDS_CONFIRMATION
    else:
        overall = Verdict.ALLOW

    return overall, resolutions


def _resolve_conflict(
    rule_a_id: str,
    rule_b_id: str,
    rules: dict[str, dict[str, Any]],
    verdict_map: dict[str, RuleVerdict],
) -> tuple[str, str]:
    """Resolve a CONFLICTS_WITH pair.

    Tiebreaking: severity > modality > scope specificity.

    Returns:
        Tuple of (winner_id, reason string).
    """
    rule_a = rules.get(rule_a_id, {})
    rule_b = rules.get(rule_b_id, {})

    # Severity comparison
    sev_a = _SEVERITY_ORDER.get(rule_a.get("severity", "LOW"), 0)
    sev_b = _SEVERITY_ORDER.get(rule_b.get("severity", "LOW"), 0)
    if sev_a != sev_b:
        winner = rule_a_id if sev_a > sev_b else rule_b_id
        return winner, (
            f"Higher severity wins: {rule_a.get('severity')} vs {rule_b.get('severity')}"
        )

    # Modality comparison
    mod_a = _MODALITY_ORDER.get(rule_a.get("modality", "INFO"), 0)
    mod_b = _MODALITY_ORDER.get(rule_b.get("modality", "INFO"), 0)
    if mod_a != mod_b:
        winner = rule_a_id if mod_a > mod_b else rule_b_id
        return winner, (
            f"Stronger modality wins: {rule_a.get('modality')} vs {rule_b.get('modality')}"
        )

    # Scope specificity: longer scope = more specific
    scope_a = rule_a.get("scope", [])
    scope_b = rule_b.get("scope", [])
    len_a = sum(len(s) for s in scope_a) if isinstance(scope_a, list) else 0
    len_b = sum(len(s) for s in scope_b) if isinstance(scope_b, list) else 0
    if len_a != len_b:
        winner = rule_a_id if len_a > len_b else rule_b_id
        return winner, "More specific scope wins"

    # Tie: first rule wins with a note
    return rule_a_id, "Tie — first rule retained (review recommended)"
