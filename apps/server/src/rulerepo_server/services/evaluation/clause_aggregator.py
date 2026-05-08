"""Clause-level verdict aggregation for the Contract Clause Engine.

Takes per-clause RuleVerdicts and aggregates them to a contract-level verdict.
The clause_verdict_map provides the breakdown for UI rendering.

See: CLAUDE.md §12.2, ADR 0004
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rulerepo_server.domain.evaluation import EvaluationResult, RuleVerdict, Verdict


@dataclass
class ClauseAggregationResult:
    """Result of aggregating clause-level verdicts to contract level.

    Attributes:
        contract_verdict: The overall contract-level verdict.
        clause_verdict_map: Mapping of clause_id to its rule verdicts.
        critical_clause_ids: Clause IDs with DENY on MUST/MUST_NOT rules.
        warning_clause_ids: Clause IDs with NEEDS_CONFIRMATION.
        clause_risk_scores: Per-clause risk score (0.0 to 1.0).
    """

    contract_verdict: Verdict
    clause_verdict_map: dict[str, list[RuleVerdict]] = field(default_factory=dict)
    critical_clause_ids: list[str] = field(default_factory=list)
    warning_clause_ids: list[str] = field(default_factory=list)
    clause_risk_scores: dict[str, float] = field(default_factory=dict)


def aggregate_clause_verdicts(
    verdicts: list[RuleVerdict],
    *,
    clause_id_extractor: ClauseIdExtractor | None = None,
) -> ClauseAggregationResult:
    """Aggregate per-clause rule verdicts into a contract-level result.

    Aggregation rules:
    - Any DENY on a MUST/MUST_NOT rule → contract-level DENY
    - Any NEEDS_CONFIRMATION on a CRITICAL severity → contract-level NEEDS_CONFIRMATION
    - Otherwise ALLOW

    Args:
        verdicts: List of RuleVerdict objects from the evaluation pipeline.
        clause_id_extractor: Optional function to extract clause_id from a verdict.
            If not provided, uses the first remediation's clause_id or "unknown".

    Returns:
        A ClauseAggregationResult with contract-level verdict and per-clause breakdown.
    """
    clause_map: dict[str, list[RuleVerdict]] = {}
    critical_ids: list[str] = []
    warning_ids: list[str] = []
    risk_scores: dict[str, float] = {}

    extractor = clause_id_extractor or _default_clause_id_extractor

    # Group verdicts by clause
    for v in verdicts:
        clause_id = extractor(v)
        clause_map.setdefault(clause_id, []).append(v)

    # Compute per-clause risk and find critical/warning clauses
    has_deny = False
    has_needs_confirmation = False

    for clause_id, clause_verdicts in clause_map.items():
        deny_count = sum(1 for cv in clause_verdicts if cv.verdict == Verdict.DENY)
        nc_count = sum(1 for cv in clause_verdicts if cv.verdict == Verdict.NEEDS_CONFIRMATION)
        total = len(clause_verdicts)

        # Risk score: proportion of violations weighted by severity
        risk = 0.0
        if total > 0:
            risk = (deny_count * 1.0 + nc_count * 0.5) / total
        risk_scores[clause_id] = min(risk, 1.0)

        if deny_count > 0:
            has_deny = True
            if clause_id not in critical_ids:
                critical_ids.append(clause_id)

        if nc_count > 0:
            has_needs_confirmation = True
            if clause_id not in warning_ids:
                warning_ids.append(clause_id)

    # Determine contract-level verdict
    if has_deny:
        contract_verdict = Verdict.DENY
    elif has_needs_confirmation:
        contract_verdict = Verdict.NEEDS_CONFIRMATION
    else:
        contract_verdict = Verdict.ALLOW

    return ClauseAggregationResult(
        contract_verdict=contract_verdict,
        clause_verdict_map=clause_map,
        critical_clause_ids=critical_ids,
        warning_clause_ids=warning_ids,
        clause_risk_scores=risk_scores,
    )


def enrich_evaluation_result(
    result: EvaluationResult,
    aggregation: ClauseAggregationResult,
) -> EvaluationResult:
    """Overlay clause aggregation onto an EvaluationResult.

    Updates the overall verdict to the contract-level verdict from
    clause aggregation.

    Args:
        result: The base evaluation result from the pipeline.
        aggregation: The clause aggregation result.

    Returns:
        The same EvaluationResult with updated verdict.
    """
    result.overall_verdict = aggregation.contract_verdict
    return result


# -- Internal helpers --

ClauseIdExtractor = type[None] | object  # callable[[RuleVerdict], str] — simplified


def _default_clause_id_extractor(verdict: RuleVerdict) -> str:
    """Extract clause_id from a RuleVerdict.

    Looks for clause_id in remediations first, then falls back to
    parsing from the issue_description or reasoning.
    """
    # Check remediations for clause_id
    for rem in verdict.remediations:
        if hasattr(rem, "clause_id") and rem.clause_id:  # type: ignore[attr-defined]
            return rem.clause_id  # type: ignore[attr-defined]

    # Try to extract from issue_description (pattern: "Clause art1: ...")
    if verdict.issue_description:
        import re

        m = re.search(r"[Cc]lause\s+(art\d+(?:\.\w+)*)", verdict.issue_description)
        if m:
            return m.group(1)

    # Try reasoning
    if verdict.reasoning:
        import re

        m = re.search(r"[Cc]lause\s+(art\d+(?:\.\w+)*)", verdict.reasoning)
        if m:
            return m.group(1)

    return "unknown"
