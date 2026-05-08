"""Regression gates -- pass/fail logic with configurable thresholds.

Compares current eval metrics against a baseline (or a perfect 1.0 on first
run) and fails the gate if precision drops by more than the threshold.

See CLAUDE.md section 13 and IMPROVEMENT.md RR-006.
"""

from __future__ import annotations

from dataclasses import dataclass

from eval_harness.metrics import MetricsResult


@dataclass
class RegressionResult:
    """Outcome of a regression gate check.

    Attributes:
        passed: Whether the gate passed.
        reason: Human-readable explanation of the outcome.
        precision_delta: Difference between baseline and current precision
            (positive means current is worse).
    """

    passed: bool = True
    reason: str = ""
    precision_delta: float = 0.0


def check_regression(
    metrics: MetricsResult,
    *,
    threshold: float = 0.05,
    baseline_precision: float | None = None,
) -> RegressionResult:
    """Check whether metrics pass the regression gate.

    Args:
        metrics: Current run metrics.
        threshold: Maximum allowed precision drop (default 5%).
        baseline_precision: Previous precision to compare against.
            If None, uses 1.0 (perfect) as baseline for first run.

    Returns:
        RegressionResult with pass/fail and reason.
    """
    if metrics.total_cases == 0:
        return RegressionResult(passed=True, reason="No test cases")

    if baseline_precision is None:
        baseline_precision = 1.0

    delta = baseline_precision - metrics.precision

    if delta > threshold:
        return RegressionResult(
            passed=False,
            reason=(
                f"Precision dropped by {delta:.3f} "
                f"(baseline: {baseline_precision:.3f}, "
                f"current: {metrics.precision:.3f}, "
                f"threshold: {threshold:.3f})"
            ),
            precision_delta=delta,
        )

    return RegressionResult(
        passed=True,
        reason="Within threshold",
        precision_delta=delta,
    )
