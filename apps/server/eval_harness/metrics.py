"""Eval harness metrics -- precision, recall, F1 computation.

Computes classification metrics from eval results, treating DENY as the
positive class (the signal we most care about detecting accurately).

See CLAUDE.md section 13 and IMPROVEMENT.md RR-006.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eval_harness.runner import EvalResult


@dataclass
class MetricsResult:
    """Aggregated metrics for a single domain's eval run.

    Attributes:
        domain: Domain name (e.g., "engineering", "legal").
        total_cases: Total number of eval cases.
        passed: Number of cases where actual verdict matched expected.
        failed: Number of cases that did not match (excluding errors).
        errors: Number of cases that produced errors.
        precision: Precision of DENY verdicts (TP / (TP + FP)).
        recall: Recall of DENY verdicts (TP / (TP + FN)).
        f1: Harmonic mean of precision and recall.
        avg_latency_ms: Mean latency across all cases.
    """

    domain: str = ""
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    precision: float = 1.0
    recall: float = 1.0
    f1: float = 1.0
    avg_latency_ms: float = 0.0


def compute_metrics(domain: str, results: list[EvalResult]) -> MetricsResult:
    """Compute precision, recall, F1 from eval results.

    Treats DENY as the positive class. When no DENY cases exist in the
    dataset, precision and recall default to 1.0 (vacuously true).

    Args:
        domain: The domain name for labeling.
        results: List of EvalResult from the runner.

    Returns:
        MetricsResult with computed statistics.
    """
    if not results:
        return MetricsResult(domain=domain)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed and r.error is None)
    errors = sum(1 for r in results if r.error is not None)

    # Precision / recall for DENY as positive class
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for r in results:
        if r.actual_verdict == "DENY" and r.expected_verdict == "DENY":
            true_positives += 1
        elif r.actual_verdict == "DENY" and r.expected_verdict != "DENY":
            false_positives += 1
        elif r.actual_verdict != "DENY" and r.expected_verdict == "DENY":
            false_negatives += 1

    tp_fp = true_positives + false_positives
    tp_fn = true_positives + false_negatives

    precision = true_positives / tp_fp if tp_fp > 0 else 1.0
    recall = true_positives / tp_fn if tp_fn > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return MetricsResult(
        domain=domain,
        total_cases=total,
        passed=passed,
        failed=failed,
        errors=errors,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        avg_latency_ms=round(avg_latency, 2),
    )
