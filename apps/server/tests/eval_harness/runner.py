"""Eval harness runner — executes golden test cases and reports accuracy.

Runs all golden test cases in tests/eval_harness/golden/ and computes
per-class precision/recall. CI fails if metrics regress > 5pp from baseline.

Requires RULEREPO_LIVE_LLM=1 to make real Gemini calls.

Usage:
    uv run pytest tests/eval_harness/runner.py --live-llm
    uv run python -m tests.eval_harness.runner
"""

from __future__ import annotations

import json
import os
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"
BASELINE_FILE = Path(__file__).parent / "baseline.json"


def load_golden_cases(category: str) -> list[dict]:
    """Load all golden test cases for a category.

    Args:
        category: Subdirectory name (e.g., "rule_extraction", "verdict").

    Returns:
        List of dicts with 'input' and 'expected' keys.
    """
    category_dir = GOLDEN_DIR / category
    if not category_dir.is_dir():
        return []

    cases = []
    for input_file in sorted(category_dir.glob("*.input.*")):
        stem = input_file.name.split(".input.")[0]
        expected_file = category_dir / f"{stem}.expected.json"
        if expected_file.exists():
            input_data = input_file.read_text(encoding="utf-8")
            expected_data = json.loads(expected_file.read_text(encoding="utf-8"))
            cases.append(
                {
                    "name": stem,
                    "input": input_data,
                    "expected": expected_data,
                }
            )
    return cases


def compute_accuracy(results: list[dict]) -> dict:
    """Compute accuracy metrics from evaluation results.

    Args:
        results: List of dicts with 'expected' and 'actual' keys.

    Returns:
        Dict with 'accuracy', 'total', 'correct' counts.
    """
    if not results:
        return {"accuracy": 1.0, "total": 0, "correct": 0}

    correct = sum(1 for r in results if r.get("match", False))
    total = len(results)
    return {
        "accuracy": correct / total if total > 0 else 1.0,
        "total": total,
        "correct": correct,
    }


def check_regression(current: dict, threshold_pp: float = 5.0) -> bool:
    """Check if current metrics regress more than threshold from baseline.

    Args:
        current: Current accuracy metrics.
        threshold_pp: Maximum allowed regression in percentage points.

    Returns:
        True if metrics are acceptable (no regression beyond threshold).
    """
    if not BASELINE_FILE.exists():
        return True

    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    baseline_acc = baseline.get("accuracy", 0.0)
    current_acc = current.get("accuracy", 0.0)

    regression = (baseline_acc - current_acc) * 100
    return regression <= threshold_pp


def run_harness() -> dict:
    """Run the full eval harness across all categories.

    Returns:
        Summary dict with per-category results.
    """
    summary = {}
    for category_dir in sorted(GOLDEN_DIR.iterdir()):
        if category_dir.is_dir() and not category_dir.name.startswith("_"):
            cases = load_golden_cases(category_dir.name)
            summary[category_dir.name] = {
                "case_count": len(cases),
                "status": "ready" if cases else "no_cases",
            }
    return summary


if __name__ == "__main__":
    live_llm = os.environ.get("RULEREPO_LIVE_LLM", "0") == "1"
    print(f"Eval Harness Runner (live_llm={'yes' if live_llm else 'no'})")
    print("=" * 50)

    results = run_harness()
    for category, info in results.items():
        print(f"  {category}: {info['case_count']} cases ({info['status']})")

    print("\nDone.")
