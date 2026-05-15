"""Deterministic evaluation layer entry point.

Dispatches on rule.kind to the appropriate deterministic evaluator.
See CLAUDE.md §14.9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.rule import (
    ComputationalBody,
    DefinitionalBody,
    NormativeBody,
    RuleBody,
    RuleKind,
)
from rulerepo_server.services.evaluation.deterministic.lookup_evaluator import (
    LookupResult,
    evaluate_lookup,
)
from rulerepo_server.services.evaluation.deterministic.numeric_evaluator import (
    NumericResult,
    evaluate_expression,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class DeterministicRuleVerdict:
    """Result from the deterministic evaluation layer for a single rule.

    Distinct from constraint.DeterministicVerdict which is an enum for the
    constraint-based evaluator. This dataclass carries richer context for
    the rule-kind-dispatched evaluation pipeline.
    """

    rule_id: str
    resolved: bool  # True if deterministic layer fully resolved this rule
    passed: bool | None = None  # None if not resolved
    numeric_result: NumericResult | None = None
    lookup_result: LookupResult | None = None
    needs_llm_followup: bool = False
    followup_context: str = ""


def evaluate_deterministic(
    *,
    rule_id: str,
    kind: RuleKind,
    body: RuleBody,
    inputs: dict[str, Any],
) -> DeterministicRuleVerdict:
    """Run deterministic evaluation for a rule.

    Dispatches by rule kind:
    - computational -> numeric_evaluator (always deterministic)
    - normative with predicate -> partial deterministic
    - principle -> skip (LLM only)
    - definitional -> reference lookup (future)
    - procedural -> state machine (future)
    """
    if kind == RuleKind.COMPUTATIONAL and isinstance(body, ComputationalBody):
        return _evaluate_computational(rule_id, body, inputs)

    if kind == RuleKind.NORMATIVE and isinstance(body, NormativeBody):
        if body.predicate:
            return _evaluate_normative_predicate(rule_id, body, inputs)
        return DeterministicRuleVerdict(rule_id=rule_id, resolved=False, needs_llm_followup=True)

    if kind == RuleKind.DEFINITIONAL and isinstance(body, DefinitionalBody):
        return _evaluate_definitional(rule_id, body, inputs)

    if kind == RuleKind.PRINCIPLE:
        return DeterministicRuleVerdict(rule_id=rule_id, resolved=False, needs_llm_followup=True)

    # Procedural — not yet implemented
    return DeterministicRuleVerdict(rule_id=rule_id, resolved=False, needs_llm_followup=True)


def _evaluate_computational(
    rule_id: str,
    body: ComputationalBody,
    inputs: dict[str, Any],
) -> DeterministicRuleVerdict:
    """Evaluate a computational rule deterministically."""
    if not body.expression:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            needs_llm_followup=True,
            followup_context="Computational rule has no expression",
        )

    result = evaluate_expression(body.expression, inputs)

    if result.error:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            needs_llm_followup=True,
            followup_context=f"Expression evaluation error: {result.error}",
        )

    # If there's an exception predicate, the deterministic result is partial
    if body.exception_predicate:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            passed=result.passed,
            numeric_result=result,
            needs_llm_followup=True,
            followup_context=(
                f"Deterministic check {'passed' if result.passed else 'failed'} "
                f"(value={result.computed_value}). "
                f"Check whether exception applies: {body.exception_predicate}"
            ),
        )

    return DeterministicRuleVerdict(
        rule_id=rule_id,
        resolved=True,
        passed=result.passed,
        numeric_result=result,
    )


def _evaluate_normative_predicate(
    rule_id: str,
    body: NormativeBody,
    inputs: dict[str, Any],
) -> DeterministicRuleVerdict:
    """Partially evaluate a normative rule with a numeric predicate."""
    if not body.predicate:
        return DeterministicRuleVerdict(rule_id=rule_id, resolved=False, needs_llm_followup=True)

    result = evaluate_expression(body.predicate, inputs)

    if result.error:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            needs_llm_followup=True,
            followup_context=f"Predicate evaluation error: {result.error}",
        )

    return DeterministicRuleVerdict(
        rule_id=rule_id,
        resolved=False,  # Normative rules always need LLM follow-up
        passed=result.passed,
        numeric_result=result,
        needs_llm_followup=True,
        followup_context=(
            f"Deterministic predicate check {'passed' if result.passed else 'failed'} "
            f"(value={result.computed_value}). "
            f"Confirm whether any exception applies and produce the final verdict."
        ),
    )


def _evaluate_definitional(
    rule_id: str,
    body: DefinitionalBody,
    inputs: dict[str, Any],
) -> DeterministicRuleVerdict:
    """Evaluate a definitional rule via lookup table.

    If the body has a ``lookup_table``, looks up the term in that table.
    Otherwise falls through to the LLM layer.
    """
    if not body.lookup_table:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            needs_llm_followup=True,
            followup_context=(
                f"Definitional rule for term '{body.term}' has no lookup table; requires LLM evaluation."
            ),
        )

    # Determine what value to look up from inputs
    lookup_value = inputs.get(body.term) or inputs.get("value")
    if lookup_value is None:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            needs_llm_followup=True,
            followup_context=(f"No value provided for term '{body.term}' in inputs."),
        )

    result = evaluate_lookup(
        table_name=body.lookup_table,
        lookup_key=body.term,
        lookup_value=lookup_value,
        must_exist=True,
    )

    if result.error:
        return DeterministicRuleVerdict(
            rule_id=rule_id,
            resolved=False,
            lookup_result=result,
            needs_llm_followup=True,
            followup_context=f"Lookup error: {result.error}",
        )

    return DeterministicRuleVerdict(
        rule_id=rule_id,
        resolved=True,
        passed=result.passed,
        lookup_result=result,
    )
