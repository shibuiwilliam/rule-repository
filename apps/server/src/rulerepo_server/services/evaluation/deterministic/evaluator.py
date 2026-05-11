"""Deterministic evaluator — checks structured constraints without calling the LLM.

This is the first layer in the Hybrid Evaluation Architecture (IMPROVEMENT.md
Proposal 9).  When a rule has structured ``constraints``, they are checked
deterministically here.  If all pass → PASS (skip LLM).  If any fail → FAIL
(skip LLM).  If constraints cannot be resolved against the available facts →
INDETERMINATE (fall through to LLM).

The evaluator never parses the rule's natural-language statement — it only
uses the structured ``constraints`` field.  This keeps the deterministic layer
fast, auditable, and predictable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.evaluation.deterministic.constraint import (
    Constraint,
    DateConstraint,
    DeterministicVerdict,
    EnumConstraint,
    NumericConstraint,
    Operator,
    constraint_from_dict,
)

logger = get_logger(__name__)


class DeterministicEvaluator:
    """Evaluates structured constraints against subject facts.

    Usage::

        evaluator = DeterministicEvaluator()
        result = evaluator.evaluate(constraints, facts)
        if result.verdict == DeterministicVerdict.FAIL:
            # skip LLM, emit DENY
    """

    def evaluate(
        self,
        constraints: list[Constraint],
        facts: dict[str, Any],
    ) -> EvaluationOutcome:
        """Check all constraints against the provided facts.

        Args:
            constraints: List of structured constraints from the rule.
            facts: Key-value pairs from the evaluation context.

        Returns:
            An ``EvaluationOutcome`` with verdict, details, and confidence.
        """
        if not constraints:
            return EvaluationOutcome(
                verdict=DeterministicVerdict.INDETERMINATE,
                details=["No constraints defined — deferring to LLM."],
                confidence=0.0,
            )

        failures: list[str] = []
        passes: list[str] = []
        indeterminate: list[str] = []

        for constraint in constraints:
            result = self._check_one(constraint, facts)
            match result:
                case (DeterministicVerdict.FAIL, msg):
                    failures.append(msg)
                case (DeterministicVerdict.PASS, msg):
                    passes.append(msg)
                case (DeterministicVerdict.INDETERMINATE, msg):
                    indeterminate.append(msg)

        if failures:
            return EvaluationOutcome(
                verdict=DeterministicVerdict.FAIL,
                details=failures,
                confidence=0.95,
            )
        if indeterminate:
            return EvaluationOutcome(
                verdict=DeterministicVerdict.INDETERMINATE,
                details=indeterminate + passes,
                confidence=0.3,
            )
        return EvaluationOutcome(
            verdict=DeterministicVerdict.PASS,
            details=passes,
            confidence=0.95,
        )

    def evaluate_from_dicts(
        self,
        constraint_dicts: list[dict],
        facts: dict[str, Any],
    ) -> EvaluationOutcome:
        """Convenience method that deserializes constraint dicts first.

        Args:
            constraint_dicts: List of serialized constraint dicts from DB/YAML.
            facts: Key-value pairs from the evaluation context.

        Returns:
            An ``EvaluationOutcome``.
        """
        parsed: list[Constraint] = []
        for cd in constraint_dicts:
            try:
                parsed.append(constraint_from_dict(cd))
            except (ValueError, KeyError) as exc:
                logger.warning("constraint_parse_failed", data=cd, error=str(exc))
        return self.evaluate(parsed, facts)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_one(
        self,
        constraint: Constraint,
        facts: dict[str, Any],
    ) -> tuple[DeterministicVerdict, str]:
        """Check a single constraint against facts."""
        match constraint:
            case NumericConstraint():
                return self._check_numeric(constraint, facts)
            case DateConstraint():
                return self._check_date(constraint, facts)
            case EnumConstraint():
                return self._check_enum(constraint, facts)

    def _check_numeric(
        self,
        c: NumericConstraint,
        facts: dict[str, Any],
    ) -> tuple[DeterministicVerdict, str]:
        value = _resolve_path(facts, c.field_path)
        if value is None:
            return (
                DeterministicVerdict.INDETERMINATE,
                f"Field '{c.field_path}' not found in facts.",
            )
        if not isinstance(value, int | float):
            try:
                value = float(value)
            except (ValueError, TypeError):
                return (
                    DeterministicVerdict.INDETERMINATE,
                    f"Field '{c.field_path}' is not numeric: {value!r}.",
                )
        unit_str = f" {c.unit}" if c.unit else ""
        if _compare(value, c.operator, c.threshold):
            return (
                DeterministicVerdict.PASS,
                f"{c.field_path}={value}{unit_str} satisfies {c.operator.value} {c.threshold}{unit_str}.",
            )
        return (
            DeterministicVerdict.FAIL,
            f"{c.field_path}={value}{unit_str} violates {c.operator.value} {c.threshold}{unit_str}.",
        )

    def _check_date(
        self,
        c: DateConstraint,
        facts: dict[str, Any],
    ) -> tuple[DeterministicVerdict, str]:
        value = _resolve_path(facts, c.field_path)
        if value is None:
            return (
                DeterministicVerdict.INDETERMINATE,
                f"Field '{c.field_path}' not found in facts.",
            )
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return (
                    DeterministicVerdict.INDETERMINATE,
                    f"Field '{c.field_path}' is not a valid date: {value!r}.",
                )
        if not isinstance(value, datetime):
            return (
                DeterministicVerdict.INDETERMINATE,
                f"Field '{c.field_path}' is not a datetime: {type(value).__name__}.",
            )
        ref = c.reference_date
        # Compare as timestamps
        if _compare(value.timestamp(), c.operator, ref.timestamp()):
            return (
                DeterministicVerdict.PASS,
                f"{c.field_path}={value.isoformat()} satisfies {c.operator.value} {ref.isoformat()}.",
            )
        return (
            DeterministicVerdict.FAIL,
            f"{c.field_path}={value.isoformat()} violates {c.operator.value} {ref.isoformat()}.",
        )

    def _check_enum(
        self,
        c: EnumConstraint,
        facts: dict[str, Any],
    ) -> tuple[DeterministicVerdict, str]:
        value = _resolve_path(facts, c.field_path)
        if value is None:
            return (
                DeterministicVerdict.INDETERMINATE,
                f"Field '{c.field_path}' not found in facts.",
            )
        str_value = str(value)
        if str_value in c.allowed_values:
            return (
                DeterministicVerdict.PASS,
                f"{c.field_path}={str_value!r} is in allowed values.",
            )
        return (
            DeterministicVerdict.FAIL,
            f"{c.field_path}={str_value!r} is not in allowed values {sorted(c.allowed_values)}.",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class EvaluationOutcome:
    """Result of deterministic constraint evaluation."""

    __slots__ = ("confidence", "details", "verdict")

    def __init__(
        self,
        verdict: DeterministicVerdict,
        details: list[str],
        confidence: float,
    ) -> None:
        self.verdict = verdict
        self.details = details
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"EvaluationOutcome(verdict={self.verdict.value}, confidence={self.confidence})"


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path in a nested dict.

    Args:
        data: The root dict (facts from evaluation context).
        path: Dot-separated key path (e.g. ``"line_items.0.amount"``).

    Returns:
        The resolved value, or ``None`` if any segment is missing.
    """
    current: Any = data
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if current is None:
            return None
    return current


def _compare(value: float, op: Operator, threshold: float) -> bool:
    """Apply a comparison operator."""
    match op:
        case Operator.LT:
            return value < threshold
        case Operator.LE:
            return value <= threshold
        case Operator.EQ:
            return value == threshold
        case Operator.GE:
            return value >= threshold
        case Operator.GT:
            return value > threshold
        case Operator.NE:
            return value != threshold
