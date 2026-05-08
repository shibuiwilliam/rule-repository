"""Eval harness runner — loads golden datasets, executes evaluations, and reports.

Usage:
    python -m eval.runner --domain engineering --dataset-dir eval/datasets --output-format table
    python -m eval.runner --tag-filter security --output-format json --output-file results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Callable, Coroutine
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from .models import DomainReport, EvalResult, GoldenCase, HarnessReport

# Type alias for the evaluation callable that the runner invokes per case.
# Signature: (subject_kind, input_payload) -> dict with keys:
#   verdict (str), rule_ids (list[str]), reasoning (str),
#   model_id (str), prompt_version (str)
EvalCallable = Callable[
    [str, dict[str, Any]],
    Coroutine[Any, Any, dict[str, Any]],
]


def _load_cases_from_yaml(path: Path) -> list[GoldenCase]:
    """Parse a YAML golden dataset file into GoldenCase instances."""
    with open(path) as f:
        data = yaml.safe_load(f)

    cases: list[GoldenCase] = []
    for raw in data.get("cases", []):
        cases.append(
            GoldenCase(
                id=raw["id"],
                domain=data.get("domain", "unknown"),
                subject_kind=raw.get("subject_kind", "code_diff"),
                description=raw.get("description", ""),
                input_payload=raw.get("input_payload", {}),
                expected_verdict=raw.get("expected_verdict", "ALLOW"),
                expected_rule_ids=raw.get("expected_rule_ids", []),
                expected_reasoning_keywords=raw.get("expected_reasoning_keywords", []),
                tags=raw.get("tags", []),
                difficulty=raw.get("difficulty", "medium"),
            )
        )
    return cases


def _compute_keyword_matches(expected: list[str], reasoning: str) -> int:
    """Count how many expected keywords appear in the reasoning text."""
    lower_reasoning = reasoning.lower()
    return sum(1 for kw in expected if kw.lower() in lower_reasoning)


def _compute_domain_metrics(
    domain: str,
    results: list[EvalResult],
    expected_verdicts: dict[str, str],
) -> DomainReport:
    """Compute precision, recall, and F1 for a domain's results.

    We treat DENY as the positive class (the interesting signal).
    """
    total = len(results)
    correct_verdict = sum(1 for r in results if r.match_verdict)

    # Precision/recall for DENY as positive class
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for r in results:
        expected = expected_verdicts.get(r.case_id, "ALLOW")
        if r.actual_verdict == "DENY" and expected == "DENY":
            true_positives += 1
        elif r.actual_verdict == "DENY" and expected != "DENY":
            false_positives += 1
        elif r.actual_verdict != "DENY" and expected == "DENY":
            false_negatives += 1

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    latencies = [r.latency_ms for r in results if r.error is None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return DomainReport(
        domain=domain,
        total=total,
        correct_verdict=correct_verdict,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        avg_latency_ms=round(avg_latency, 2),
        cases=results,
    )


class EvalRunner:
    """Loads golden datasets and runs evaluations against a callable backend.

    Args:
        eval_fn: Async callable that performs evaluation. Accepts
            (subject_kind, input_payload) and returns a dict with keys:
            verdict, rule_ids, reasoning, model_id, prompt_version.
        dataset_dir: Path to the root datasets directory.
    """

    def __init__(
        self,
        eval_fn: EvalCallable,
        dataset_dir: str | Path = "eval/datasets",
    ) -> None:
        self._eval_fn = eval_fn
        self._dataset_dir = Path(dataset_dir)
        self._cases: dict[str, list[GoldenCase]] = {}

    def load_datasets(
        self,
        domains: list[str] | None = None,
        tag_filter: list[str] | None = None,
        difficulty_filter: str | None = None,
    ) -> None:
        """Load golden cases from YAML files, optionally filtered.

        Args:
            domains: If provided, only load these domains.
            tag_filter: If provided, keep only cases with at least one matching tag.
            difficulty_filter: If provided, keep only cases with this difficulty.
        """
        self._cases.clear()

        if not self._dataset_dir.exists():
            return

        for domain_dir in sorted(self._dataset_dir.iterdir()):
            if not domain_dir.is_dir():
                continue

            domain_name = domain_dir.name
            if domains and domain_name not in domains:
                continue

            domain_cases: list[GoldenCase] = []
            for yaml_file in sorted(domain_dir.glob("*.yaml")):
                domain_cases.extend(_load_cases_from_yaml(yaml_file))

            # Apply filters
            if tag_filter:
                tag_set = set(tag_filter)
                domain_cases = [c for c in domain_cases if tag_set & set(c.tags)]

            if difficulty_filter:
                domain_cases = [c for c in domain_cases if c.difficulty == difficulty_filter]

            if domain_cases:
                self._cases[domain_name] = domain_cases

    async def _run_case(self, case: GoldenCase) -> EvalResult:
        """Evaluate a single golden case and return the result."""
        start = time.monotonic()
        try:
            response = await self._eval_fn(case.subject_kind, case.input_payload)
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return EvalResult(
                case_id=case.id,
                latency_ms=round(elapsed, 2),
                error=str(exc),
            )

        elapsed = (time.monotonic() - start) * 1000

        actual_verdict = response.get("verdict", "")
        actual_rule_ids = response.get("rule_ids", [])
        actual_reasoning = response.get("reasoning", "")
        model_id = response.get("model_id", "")
        prompt_version = response.get("prompt_version", "")

        match_verdict = actual_verdict == case.expected_verdict

        # Rule matching: if expected is empty, we don't penalize
        match_rules = set(actual_rule_ids) == set(case.expected_rule_ids) if case.expected_rule_ids else True

        keyword_hits = _compute_keyword_matches(case.expected_reasoning_keywords, actual_reasoning)

        return EvalResult(
            case_id=case.id,
            actual_verdict=actual_verdict,
            actual_rule_ids=actual_rule_ids,
            actual_reasoning=actual_reasoning,
            match_verdict=match_verdict,
            match_rules=match_rules,
            keyword_hits=keyword_hits,
            keyword_total=len(case.expected_reasoning_keywords),
            latency_ms=round(elapsed, 2),
            model_id=model_id,
            prompt_version=prompt_version,
        )

    async def run_domain(self, domain: str) -> DomainReport:
        """Run all loaded cases for a single domain.

        Args:
            domain: Domain name to run.

        Returns:
            DomainReport with per-case results and aggregated metrics.

        Raises:
            KeyError: If the domain has no loaded cases.
        """
        cases = self._cases.get(domain)
        if not cases:
            raise KeyError(f"No loaded cases for domain '{domain}'")

        results: list[EvalResult] = []
        for case in cases:
            result = await self._run_case(case)
            results.append(result)

        expected_verdicts = {c.id: c.expected_verdict for c in cases}
        return _compute_domain_metrics(domain, results, expected_verdicts)

    async def run(
        self,
        domains: list[str] | None = None,
        tag_filter: list[str] | None = None,
        difficulty_filter: str | None = None,
    ) -> HarnessReport:
        """Run the full eval harness across loaded (or freshly loaded) datasets.

        Args:
            domains: Optional domain filter (passed to load_datasets if
                cases haven't been loaded yet).
            tag_filter: Optional tag filter.
            difficulty_filter: Optional difficulty filter.

        Returns:
            HarnessReport with per-domain reports and overall metrics.
        """
        if not self._cases:
            self.load_datasets(
                domains=domains,
                tag_filter=tag_filter,
                difficulty_filter=difficulty_filter,
            )

        domain_reports: list[DomainReport] = []
        all_model_ids: set[str] = set()
        prompt_versions: dict[str, str] = {}

        target_domains = domains if domains else list(self._cases.keys())

        for domain in sorted(target_domains):
            if domain not in self._cases:
                continue
            report = await self.run_domain(domain)
            domain_reports.append(report)

            for case_result in report.cases:
                if case_result.model_id:
                    all_model_ids.add(case_result.model_id)
                if case_result.prompt_version:
                    prompt_versions[domain] = case_result.prompt_version

        # Weighted overall F1
        total_cases = sum(r.total for r in domain_reports)
        overall_f1 = sum(r.f1 * r.total for r in domain_reports) / total_cases if total_cases > 0 else 0.0

        return HarnessReport(
            domains=domain_reports,
            overall_f1=round(overall_f1, 4),
            prompt_versions=prompt_versions,
            model_ids=sorted(all_model_ids),
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rule Repository Eval Harness — measure LLM verdict accuracy",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Run only this domain (e.g., engineering, hr, legal, content)",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="eval/datasets",
        help="Path to golden datasets directory",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write JSON output to this file (only with --output-format json)",
    )
    parser.add_argument(
        "--tag-filter",
        type=str,
        nargs="*",
        default=None,
        help="Only run cases with at least one of these tags",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default=None,
        help="Only run cases with this difficulty",
    )
    return parser.parse_args(argv)


async def _stub_eval_fn(subject_kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Stub evaluation function for dry-run / smoke-test mode.

    Returns ALLOW for everything. Replace with a real evaluation service
    call when running against a live stack.
    """
    return {
        "verdict": "ALLOW",
        "rule_ids": [],
        "reasoning": "Stub evaluator — no real evaluation performed.",
        "model_id": "stub",
        "prompt_version": "stub-v0",
    }


async def _main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    domains = [args.domain] if args.domain else None

    runner = EvalRunner(
        eval_fn=_stub_eval_fn,
        dataset_dir=args.dataset_dir,
    )
    runner.load_datasets(
        domains=domains,
        tag_filter=args.tag_filter,
        difficulty_filter=args.difficulty,
    )

    report = await runner.run(domains=domains)

    if args.output_format == "table":
        from .reporters.console import ConsoleReporter

        ConsoleReporter().print_report(report)
    else:
        from .reporters.json_reporter import JsonReporter

        if args.output_file:
            JsonReporter().write_report(report, args.output_file)
            sys.stdout.write(f"Report written to {args.output_file}\n")
        else:
            sys.stdout.write(json.dumps(asdict(report), indent=2, default=str) + "\n")


if __name__ == "__main__":
    asyncio.run(_main())
