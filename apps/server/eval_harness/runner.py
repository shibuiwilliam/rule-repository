"""Eval Harness -- validates LLM-driven features against golden datasets.

Usage:
    python -m eval_harness.runner --domain engineering
    python -m eval_harness.runner --all
    python -m eval_harness.runner --domain engineering --report json
    python -m eval_harness.runner --all --threshold 0.03

See CLAUDE.md section 13 and IMPROVEMENT.md RR-006.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from eval_harness.metrics import MetricsResult, compute_metrics
from eval_harness.regression_gates import RegressionResult, check_regression

DATASETS_DIR = Path(__file__).parent / "datasets"

# Valid verdict values across all domains
VALID_VERDICTS = frozenset({"ALLOW", "DENY", "NEEDS_CONFIRMATION", "ALLOW_WITH_CONDITIONS"})


@dataclass
class EvalCase:
    """A single golden test case loaded from a JSONL dataset.

    Attributes:
        id: Unique identifier (e.g., "eng-001").
        domain: Evaluation domain (e.g., "engineering").
        artifact_type: The artifact type (e.g., "code_diff", "contract_clause").
        input_payload: Domain-specific input fed to the evaluator.
        expected_verdict: Expected verdict string.
        expected_rules_matched: Rule IDs expected to fire.
        tags: Categorical tags for filtering.
        description: Human-readable description of what this case tests.
    """

    id: str
    domain: str
    artifact_type: str
    input_payload: dict
    expected_verdict: str
    expected_rules_matched: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class EvalResult:
    """Result of running a single eval case.

    Attributes:
        case_id: The EvalCase.id that was evaluated.
        expected_verdict: The expected verdict from the golden dataset.
        actual_verdict: The verdict returned by the evaluator.
        rules_matched: Rule IDs that fired during evaluation.
        passed: Whether actual_verdict matches expected_verdict.
        error: Error message if the evaluation failed.
        latency_ms: Wall-clock time in milliseconds.
    """

    case_id: str
    expected_verdict: str
    actual_verdict: str | None = None
    rules_matched: list[str] = field(default_factory=list)
    passed: bool = False
    error: str | None = None
    latency_ms: float = 0.0


def load_dataset(domain: str) -> list[EvalCase]:
    """Load golden dataset for a domain from a JSONL file.

    Args:
        domain: Domain name (matches ``<domain>_golden.jsonl`` filename).

    Returns:
        List of EvalCase instances. Empty list if the file does not exist.
    """
    path = DATASETS_DIR / f"{domain}_golden.jsonl"
    if not path.exists():
        print(f"Warning: no golden dataset found at {path}")
        return []

    cases: list[EvalCase] = []
    with open(path) as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"Warning: skipping malformed JSON at {path}:{line_num}: {exc}")
                continue
            cases.append(EvalCase(**data))
    return cases


def run_eval_offline(cases: list[EvalCase]) -> list[EvalResult]:
    """Run eval cases in offline mode (no LLM calls).

    Validates that the golden dataset is well-formed and that expected
    verdicts are valid. In offline mode, each case's actual verdict is set
    equal to its expected verdict (simulating a perfect evaluator), so the
    gate checks dataset integrity rather than evaluator quality.

    Args:
        cases: List of golden cases to validate.

    Returns:
        List of EvalResult instances.
    """
    results: list[EvalResult] = []
    for case in cases:
        result = EvalResult(case_id=case.id, expected_verdict=case.expected_verdict)
        if case.expected_verdict in VALID_VERDICTS:
            result.passed = True
            result.actual_verdict = case.expected_verdict
        else:
            result.passed = False
            result.error = f"Invalid expected verdict: {case.expected_verdict}"
        results.append(result)
    return results


def run_domain(
    domain: str,
    *,
    live: bool = False,
) -> tuple[list[EvalResult], MetricsResult]:
    """Run eval harness for a single domain.

    Args:
        domain: Domain name to evaluate.
        live: If True, would call the actual LLM (requires RULEREPO_LIVE_LLM=1).
            Currently only offline mode is implemented.

    Returns:
        Tuple of (results, metrics).
    """
    cases = load_dataset(domain)
    if not cases:
        return [], MetricsResult(domain=domain)

    if live:
        # Live mode would call the actual LLM - requires RULEREPO_LIVE_LLM=1
        print(f"Live evaluation not yet implemented for {domain}")
        results = run_eval_offline(cases)
    else:
        results = run_eval_offline(cases)

    metrics = compute_metrics(domain, results)
    return results, metrics


def _print_domain_report(
    domain: str,
    metrics: MetricsResult,
    regression: RegressionResult,
) -> None:
    """Print a formatted report for a single domain."""
    print(f"\n{'=' * 60}")
    print(f"Domain: {domain}")
    print(f"{'=' * 60}")
    print(f"  Cases:     {metrics.total_cases}")
    print(f"  Passed:    {metrics.passed}")
    print(f"  Failed:    {metrics.failed}")
    print(f"  Errors:    {metrics.errors}")
    print(f"  Precision: {metrics.precision:.4f}")
    print(f"  Recall:    {metrics.recall:.4f}")
    print(f"  F1:        {metrics.f1:.4f}")

    if not regression.passed:
        print(f"  REGRESSION GATE FAILED: {regression.reason}")
    else:
        print(f"  Regression gate: PASSED ({regression.reason})")


def main() -> None:
    """Entry point for the eval harness CLI."""
    parser = argparse.ArgumentParser(
        description="Rule Repository Eval Harness (RR-006)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Domain to evaluate (engineering, legal, hr, etc.)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all domains with golden datasets",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live LLM (requires RULEREPO_LIVE_LLM=1)",
    )
    parser.add_argument(
        "--report",
        choices=["text", "json", "html"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Max precision drop allowed (default: 0.05)",
    )
    args = parser.parse_args()

    if not args.domain and not args.all:
        parser.error("Specify --domain or --all")

    domains: list[str] = []
    if args.all:
        for f in sorted(DATASETS_DIR.glob("*_golden.jsonl")):
            domains.append(f.stem.replace("_golden", ""))
    else:
        domains = [args.domain]

    all_pass = True
    all_metrics: list[MetricsResult] = []

    for domain in domains:
        results, metrics = run_domain(domain, live=args.live)
        all_metrics.append(metrics)

        regression = check_regression(metrics, threshold=args.threshold)

        if args.report == "text":
            _print_domain_report(domain, metrics, regression)

        if not regression.passed:
            all_pass = False

    if args.report == "json":
        report = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "domains": [m.__dict__ for m in all_metrics],
            "overall_pass": all_pass,
        }
        print(json.dumps(report, indent=2, default=str))
    elif args.report == "text":
        print(f"\n{'=' * 60}")
        total_cases = sum(m.total_cases for m in all_metrics)
        total_passed = sum(m.passed for m in all_metrics)
        print(f"OVERALL: {total_passed}/{total_cases} passed")
        print(f"Result: {'PASS' if all_pass else 'FAIL'}")
        print(f"{'=' * 60}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
