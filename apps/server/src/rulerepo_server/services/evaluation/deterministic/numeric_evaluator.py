"""Deterministic numeric evaluator using asteval.

Evaluates computational rule expressions in a sandboxed environment.
No I/O, no imports, no attribute access per CLAUDE.md §14.9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class NumericResult:
    """Result of a deterministic numeric evaluation."""

    passed: bool
    computed_value: Any = None
    expression: str = ""
    error: str | None = None


def evaluate_expression(
    expression: str,
    inputs: dict[str, Any],
) -> NumericResult:
    """Evaluate a computational rule expression deterministically.

    Uses asteval for sandboxed evaluation: no I/O, no imports,
    no attribute access.

    Args:
        expression: The expression to evaluate (e.g., "total <= 45")
        inputs: Variable bindings for the expression

    Returns:
        NumericResult with pass/fail and computed value.
    """
    try:
        import asteval
    except ImportError:
        return NumericResult(
            passed=False,
            expression=expression,
            error="asteval not installed",
        )

    aeval = asteval.Interpreter(
        use_numpy=False,
        max_time=5.0,  # 5 second timeout
    )

    # Disable dangerous features
    for attr in ("import", "importlib", "__import__"):
        if attr in aeval.symtable:
            del aeval.symtable[attr]

    # Bind inputs
    for name, value in inputs.items():
        aeval.symtable[name] = value

    # Also provide common builtins for expressions
    aeval.symtable["sum"] = sum
    aeval.symtable["min"] = min
    aeval.symtable["max"] = max
    aeval.symtable["abs"] = abs
    aeval.symtable["len"] = len

    result = aeval(expression)

    if aeval.error:
        error_msgs = "; ".join(str(e.get_error()) for e in aeval.error)
        logger.warning("numeric_evaluation_error", expression=expression, error=error_msgs)
        return NumericResult(
            passed=False,
            expression=expression,
            error=error_msgs,
        )

    # The expression should evaluate to a boolean
    if isinstance(result, bool):
        return NumericResult(passed=result, computed_value=result, expression=expression)

    # If it returns a number, treat it as truthy/falsy
    return NumericResult(
        passed=bool(result),
        computed_value=result,
        expression=expression,
    )
