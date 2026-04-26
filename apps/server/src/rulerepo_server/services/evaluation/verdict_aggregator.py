"""Verdict Aggregator — combines per-rule verdicts into an overall EvaluationResult.

Per CLAUDE_ENHANCE.md §1.4.4:
- If any DENY → overall DENY
- Else if any NEEDS_CONFIRMATION → overall NEEDS_CONFIRMATION
- Else → overall ALLOW
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from rulerepo_server.domain.evaluation import EvaluationResult, RuleVerdict, Verdict


def aggregate_verdicts(
    rule_verdicts: list[RuleVerdict],
    model_ids: list[str],
    total_latency_ms: int,
) -> EvaluationResult:
    """Aggregate per-rule verdicts into a single EvaluationResult.

    Args:
        rule_verdicts: List of individual rule verdicts.
        model_ids: List of model IDs used in evaluation.
        total_latency_ms: Total evaluation latency in milliseconds.

    Returns:
        An EvaluationResult with overall verdict and fix summary.
    """
    if not rule_verdicts:
        return EvaluationResult(
            evaluation_id=str(uuid4()),
            overall_verdict=Verdict.ALLOW,
            rule_verdicts=[],
            rules_evaluated=0,
            rules_passed=0,
            rules_violated=0,
            rules_uncertain=0,
            fix_summary=None,
            model_ids_used=model_ids,
            total_latency_ms=total_latency_ms,
        )

    # Determine overall verdict
    has_deny = any(v.verdict == Verdict.DENY for v in rule_verdicts)
    has_uncertain = any(v.verdict == Verdict.NEEDS_CONFIRMATION for v in rule_verdicts)

    if has_deny:
        overall = Verdict.DENY
    elif has_uncertain:
        overall = Verdict.NEEDS_CONFIRMATION
    else:
        overall = Verdict.ALLOW

    # Count by verdict type
    passed = sum(1 for v in rule_verdicts if v.verdict == Verdict.ALLOW)
    violated = sum(1 for v in rule_verdicts if v.verdict == Verdict.DENY)
    uncertain = sum(1 for v in rule_verdicts if v.verdict == Verdict.NEEDS_CONFIRMATION)

    # Build fix summary from DENY verdicts
    fix_summary = _build_fix_summary(rule_verdicts)

    return EvaluationResult(
        evaluation_id=str(uuid4()),
        overall_verdict=overall,
        rule_verdicts=rule_verdicts,
        rules_evaluated=len(rule_verdicts),
        rules_passed=passed,
        rules_violated=violated,
        rules_uncertain=uncertain,
        fix_summary=fix_summary,
        model_ids_used=list(set(model_ids)),
        total_latency_ms=total_latency_ms,
        timestamp=datetime.now(tz=timezone.utc),
    )


def _build_fix_summary(verdicts: list[RuleVerdict]) -> str | None:
    """Build a numbered fix summary from DENY verdicts.

    Per CLAUDE_ENHANCE.md §1.4.4: if there are DENY verdicts, concatenate
    their fix_suggestion fields into a numbered list.
    """
    violations = [v for v in verdicts if v.verdict == Verdict.DENY and v.fix_suggestion]
    warnings = [
        v for v in verdicts if v.verdict == Verdict.NEEDS_CONFIRMATION and v.issue_description
    ]

    if not violations and not warnings:
        return None

    lines: list[str] = []
    if violations:
        lines.append(f"Fix {len(violations)} violation(s):")
        for i, v in enumerate(violations, 1):
            lines.append(f"  {i}. {v.fix_suggestion}")

    if warnings:
        lines.append(f"\nReview {len(warnings)} warning(s):")
        for i, w in enumerate(warnings, 1):
            lines.append(f"  {i}. {w.issue_description}")

    return "\n".join(lines)
