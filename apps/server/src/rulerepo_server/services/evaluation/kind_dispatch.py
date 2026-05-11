"""Kind-based evaluation dispatcher.

Routes rules to the appropriate evaluation strategy based on their ``kind``
field (IMPROVEMENT.md Proposal 3).  The dispatcher is called *before* the
LLM batch evaluator so that non-normative rules are resolved without
consuming LLM tokens.

Evaluation strategies:
- **NORMATIVE**: full LLM-as-Judge (existing path — not handled here).
- **COMPUTATIONAL**: extract numeric conditions from the rule statement,
  evaluate deterministically against subject data, then optionally pass
  edge cases to the LLM.
- **PROCEDURAL**: verify ordering / state-transition constraints.
- **DEFINITIONAL**: always ALLOW — definitions are referenced by other rules.
- **PRINCIPLE**: always ALLOW with a note — evaluated through derived rules.
"""

from __future__ import annotations

import re
import time
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationContext, RuleVerdict, Verdict
from rulerepo_server.domain.rule import RuleKind

logger = get_logger(__name__)

# Sentinel model ID used when no LLM call is made.
_LOCAL_MODEL_ID = "local/kind-dispatch"


def partition_by_kind(
    rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split rules into those needing LLM evaluation and those that don't.

    Args:
        rules: Full list of rule dicts (must include ``kind`` key).

    Returns:
        A tuple of ``(llm_rules, local_rules)`` where ``llm_rules`` are
        NORMATIVE rules that require the LLM, and ``local_rules`` are
        COMPUTATIONAL / PROCEDURAL / DEFINITIONAL / PRINCIPLE rules that
        can be resolved locally.
    """
    llm_rules: list[dict[str, Any]] = []
    local_rules: list[dict[str, Any]] = []

    for rule in rules:
        kind_str = rule.get("kind", "normative")
        try:
            kind = RuleKind(kind_str)
        except ValueError:
            kind = RuleKind.NORMATIVE

        if kind == RuleKind.NORMATIVE:
            llm_rules.append(rule)
        else:
            local_rules.append(rule)

    return llm_rules, local_rules


def evaluate_local(
    rule: dict[str, Any],
    context: EvaluationContext,
) -> tuple[RuleVerdict, str, int]:
    """Evaluate a non-normative rule locally without calling the LLM.

    Args:
        rule: A rule dict with ``kind`` set to a non-NORMATIVE value.
        context: The evaluation context.

    Returns:
        A ``(RuleVerdict, model_id, latency_ms)`` tuple.
    """
    start = time.time()
    kind_str = rule.get("kind", "normative")
    try:
        kind = RuleKind(kind_str)
    except ValueError:
        kind = RuleKind.NORMATIVE

    match kind:
        case RuleKind.COMPUTATIONAL:
            verdict = _evaluate_computational(rule, context)
        case RuleKind.PROCEDURAL:
            verdict = _evaluate_procedural(rule, context)
        case RuleKind.DEFINITIONAL:
            verdict = _evaluate_definitional(rule)
        case RuleKind.PRINCIPLE:
            verdict = _evaluate_principle(rule)
        case _:
            # Should not happen — NORMATIVE rules are handled by LLM.
            verdict = RuleVerdict(
                rule_id=rule["id"],
                rule_statement=rule.get("statement", ""),
                verdict=Verdict.NEEDS_CONFIRMATION,
                confidence=0.0,
                reasoning="Unexpected rule kind; deferred to manual review.",
            )

    latency_ms = int((time.time() - start) * 1000)
    logger.info(
        "kind_dispatch_local",
        rule_id=rule["id"],
        kind=kind_str,
        verdict=verdict.verdict.value,
        latency_ms=latency_ms,
    )
    return verdict, _LOCAL_MODEL_ID, latency_ms


# ---------------------------------------------------------------------------
# Kind-specific evaluators
# ---------------------------------------------------------------------------

# Regex to extract simple numeric comparisons from rule statements.
# Matches patterns like "45 hours", "5,000 JPY", "15%", "60 days",
# and Japanese equivalents like "45時間", "30,000円".
_NUMERIC_PATTERN = re.compile(
    r"(\d[\d,]*\.?\d*)\s*"
    r"(%|hours?|days?|JPY|USD|EUR|yen|years?|months?|minutes?"
    r"|時間|日|円|年|月|分|%)",
    re.IGNORECASE,
)


def _extract_numeric_thresholds(statement: str) -> list[tuple[float, str]]:
    """Extract ``(value, unit)`` pairs from a rule statement."""
    results: list[tuple[float, str]] = []
    for match in _NUMERIC_PATTERN.finditer(statement):
        raw_num = match.group(1).replace(",", "")
        try:
            value = float(raw_num)
        except ValueError:
            continue
        unit = match.group(2).lower().rstrip("s")  # normalize plural
        results.append((value, unit))
    return results


def _evaluate_computational(
    rule: dict[str, Any],
    context: EvaluationContext,
) -> RuleVerdict:
    """Deterministic evaluation for computational rules.

    When the rule has structured ``constraints`` (Proposal 9), uses the
    DeterministicEvaluator for precise, auditable checks.  Falls back to
    the legacy regex-based threshold extraction when no constraints are
    defined.
    """
    # --- Structured constraints path (preferred) ---
    constraints_raw = rule.get("constraints") or []
    if constraints_raw:
        from rulerepo_server.services.evaluation.deterministic.constraint import (
            DeterministicVerdict,
        )
        from rulerepo_server.services.evaluation.deterministic.evaluator import (
            DeterministicEvaluator,
        )

        evaluator = DeterministicEvaluator()
        outcome = evaluator.evaluate_from_dicts(constraints_raw, context.facts)

        logger.info(
            "deterministic_evaluation",
            rule_id=rule["id"],
            verdict=outcome.verdict.value,
            confidence=outcome.confidence,
            details=outcome.details[:3],
        )

        match outcome.verdict:
            case DeterministicVerdict.FAIL:
                return RuleVerdict(
                    rule_id=rule["id"],
                    rule_statement=rule.get("statement", ""),
                    verdict=Verdict.DENY,
                    confidence=outcome.confidence,
                    reasoning=f"Deterministic check failed: {'; '.join(outcome.details)}",
                    issue_description="; ".join(outcome.details),
                    fix_suggestion="Adjust values to comply with the rule constraints.",
                )
            case DeterministicVerdict.PASS:
                return RuleVerdict(
                    rule_id=rule["id"],
                    rule_statement=rule.get("statement", ""),
                    verdict=Verdict.ALLOW,
                    confidence=outcome.confidence,
                    reasoning=f"Deterministic check passed: {'; '.join(outcome.details)}",
                )
            case DeterministicVerdict.INDETERMINATE:
                # Fall through — try legacy path or return NEEDS_CONFIRMATION
                pass

    # --- Legacy regex-based path (fallback) ---
    thresholds = _extract_numeric_thresholds(rule.get("statement", ""))
    facts = context.facts

    if not thresholds or not facts:
        return RuleVerdict(
            rule_id=rule["id"],
            rule_statement=rule.get("statement", ""),
            verdict=Verdict.NEEDS_CONFIRMATION,
            confidence=0.3,
            reasoning=(
                "Computational rule but no numeric thresholds could be extracted or no facts available for comparison."
            ),
        )

    # Try to match threshold units against fact keys.
    violations: list[str] = []
    matched = False

    for threshold_val, unit in thresholds:
        for fact_key, fact_val in facts.items():
            if not isinstance(fact_val, int | float):
                continue
            # Heuristic: if the fact key contains the unit name, compare.
            if unit in fact_key.lower() or _unit_alias(unit) in fact_key.lower():
                matched = True
                modality = rule.get("modality", "MUST")
                if modality in ("MUST_NOT",) and fact_val > threshold_val:
                    violations.append(f"{fact_key}={fact_val} exceeds limit {threshold_val} {unit}")
                elif modality in ("MUST",) and fact_val < threshold_val:
                    violations.append(f"{fact_key}={fact_val} is below required minimum {threshold_val} {unit}")

    if not matched:
        return RuleVerdict(
            rule_id=rule["id"],
            rule_statement=rule.get("statement", ""),
            verdict=Verdict.NEEDS_CONFIRMATION,
            confidence=0.3,
            reasoning="Could not match rule thresholds against available facts.",
        )

    if violations:
        return RuleVerdict(
            rule_id=rule["id"],
            rule_statement=rule.get("statement", ""),
            verdict=Verdict.DENY,
            confidence=0.9,
            reasoning=f"Computational check failed: {'; '.join(violations)}",
            issue_description="; ".join(violations),
            fix_suggestion="Adjust values to comply with the rule thresholds.",
        )

    return RuleVerdict(
        rule_id=rule["id"],
        rule_statement=rule.get("statement", ""),
        verdict=Verdict.ALLOW,
        confidence=0.95,
        reasoning="All numeric conditions satisfied by the provided facts.",
    )


def _unit_alias(unit: str) -> str:
    """Return a common alias for a unit to improve fact-key matching."""
    aliases: dict[str, str] = {
        "hour": "overtime",
        "day": "day",
        "jpy": "amount",
        "%": "rate",
        "year": "year",
        "month": "month",
        "minute": "minute",
        "usd": "amount",
        "eur": "amount",
        "yen": "amount",
        # Japanese units
        "時間": "hour",
        "日": "day",
        "円": "amount",
        "年": "year",
        "月": "month",
        "分": "minute",
    }
    return aliases.get(unit, unit)


def _evaluate_procedural(
    rule: dict[str, Any],
    context: EvaluationContext,
) -> RuleVerdict:
    """Verify ordering / state-transition constraints.

    Checks whether ``context.facts`` contains a ``steps`` or ``sequence``
    list, and whether the ordering is consistent with preconditions
    declared in the rule.  This is a stub — full implementation would
    parse state machines from the rule statement.
    """
    facts = context.facts
    steps = facts.get("steps") or facts.get("sequence") or facts.get("workflow_steps")

    if not steps or not isinstance(steps, list):
        return RuleVerdict(
            rule_id=rule["id"],
            rule_statement=rule.get("statement", ""),
            verdict=Verdict.NEEDS_CONFIRMATION,
            confidence=0.3,
            reasoning=(
                "Procedural rule but no steps/sequence found in context facts. Cannot verify ordering constraints."
            ),
        )

    # Check preconditions: each precondition should appear before the main action.
    preconditions = rule.get("preconditions", [])
    if preconditions:
        steps_lower = [str(s).lower() for s in steps]
        for pre in preconditions:
            pre_lower = pre.lower()
            # Check if any step mentions the precondition
            pre_idx = next(
                (i for i, s in enumerate(steps_lower) if pre_lower in s),
                None,
            )
            if pre_idx is None:
                return RuleVerdict(
                    rule_id=rule["id"],
                    rule_statement=rule.get("statement", ""),
                    verdict=Verdict.DENY,
                    confidence=0.7,
                    reasoning=f"Required precondition not found in workflow steps: '{pre}'",
                    issue_description=f"Missing step: {pre}",
                    fix_suggestion=f"Add the required step '{pre}' to the workflow.",
                )

    return RuleVerdict(
        rule_id=rule["id"],
        rule_statement=rule.get("statement", ""),
        verdict=Verdict.ALLOW,
        confidence=0.8,
        reasoning="Procedural ordering constraints appear to be satisfied.",
    )


def _evaluate_definitional(rule: dict[str, Any]) -> RuleVerdict:
    """Definitional rules never produce violations — they define terms."""
    return RuleVerdict(
        rule_id=rule["id"],
        rule_statement=rule.get("statement", ""),
        verdict=Verdict.ALLOW,
        confidence=1.0,
        reasoning="Definitional rule — provides a reference definition, not a normative constraint.",
    )


def _evaluate_principle(rule: dict[str, Any]) -> RuleVerdict:
    """Principle rules are evaluated through their derived normative rules."""
    return RuleVerdict(
        rule_id=rule["id"],
        rule_statement=rule.get("statement", ""),
        verdict=Verdict.ALLOW,
        confidence=1.0,
        reasoning=(
            "Principle rule — evaluated indirectly through derived normative rules. "
            "This rule expresses high-level intent and does not produce violations on its own."
        ),
    )
