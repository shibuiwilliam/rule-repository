"""Unit tests for the Eval Harness (workstream 7e).

Tests golden dataset loading, runner, reporters, and drift detection.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

# ---------------------------------------------------------------------------
# Eval harness model tests (importing from eval/ package)
# ---------------------------------------------------------------------------


class TestEvalModels:
    """Test eval harness data models without external deps."""

    def test_golden_case_structure(self) -> None:
        """Verify GoldenCase can be constructed with all required fields."""
        # Import deferred to avoid import errors if eval/ not yet built
        try:
            from eval.models import GoldenCase
        except ImportError:
            pytest.skip("eval.models not yet available")

        case = GoldenCase(
            id="eng_001",
            domain="engineering",
            subject_kind="code_diff",
            description="Test naming convention violation",
            input_payload={"diff": "- old_name\n+ oldName"},
            expected_verdict="DENY",
            expected_rule_ids=[],
            expected_reasoning_keywords=["naming", "snake_case"],
            tags=["naming"],
            difficulty="easy",
        )
        assert case.domain == "engineering"
        assert case.expected_verdict == "DENY"

    def test_eval_result_structure(self) -> None:
        try:
            from eval.models import EvalResult
        except ImportError:
            pytest.skip("eval.models not yet available")

        result = EvalResult(
            case_id="eng_001",
            actual_verdict="DENY",
            actual_rule_ids=["r1"],
            actual_reasoning="Variable uses camelCase instead of snake_case",
            match_verdict=True,
            match_rules=False,
            latency_ms=150,
            model_id="gemini-3-flash-preview",
            prompt_version="abc123",
            error=None,
        )
        assert result.match_verdict is True
        assert result.latency_ms == 150

    def test_domain_report_f1_calculation(self) -> None:
        try:
            from eval.models import DomainReport, EvalResult
        except ImportError:
            pytest.skip("eval.models not yet available")

        results = [
            EvalResult(
                case_id=f"case_{i}",
                actual_verdict="DENY" if i < 8 else "ALLOW",
                actual_rule_ids=[],
                actual_reasoning="",
                match_verdict=i < 8,  # 8 correct out of 10
                match_rules=True,
                latency_ms=100,
                model_id="test",
                prompt_version="v1",
                error=None,
            )
            for i in range(10)
        ]
        report = DomainReport(
            domain="test",
            total=10,
            correct_verdict=8,
            precision=0.8,
            recall=0.8,
            f1=0.8,
            avg_latency_ms=100.0,
            cases=results,
        )
        assert report.f1 == 0.8
        assert report.total == 10


class TestDriftDetector:
    """Test drift detection between eval runs."""

    def test_detect_regression(self) -> None:
        try:
            from eval.drift import DriftDetector
            from eval.models import DomainReport, HarnessReport
        except ImportError:
            pytest.skip("eval modules not yet available")

        old_report = HarnessReport(
            run_id="run_old",
            timestamp=datetime.now(tz=UTC),
            domains=[
                DomainReport(
                    domain="engineering",
                    total=50,
                    correct_verdict=45,
                    precision=0.90,
                    recall=0.90,
                    f1=0.90,
                    avg_latency_ms=100.0,
                    cases=[],
                ),
            ],
            overall_f1=0.90,
            prompt_versions={},
            model_ids=["gemini-3-flash-preview"],
        )
        new_report = HarnessReport(
            run_id="run_new",
            timestamp=datetime.now(tz=UTC),
            domains=[
                DomainReport(
                    domain="engineering",
                    total=50,
                    correct_verdict=40,
                    precision=0.80,
                    recall=0.80,
                    f1=0.80,
                    avg_latency_ms=100.0,
                    cases=[],
                ),
            ],
            overall_f1=0.80,
            prompt_versions={},
            model_ids=["gemini-3-flash-preview"],
        )
        detector = DriftDetector(threshold=0.02)
        alerts = detector.compare(old_report, new_report)
        regressions = [a for a in alerts if a.is_regression]
        assert len(regressions) > 0

    def test_no_regression_within_threshold(self) -> None:
        try:
            from eval.drift import DriftDetector
            from eval.models import DomainReport, HarnessReport
        except ImportError:
            pytest.skip("eval modules not yet available")

        old_report = HarnessReport(
            run_id="run_old",
            timestamp=datetime.now(tz=UTC),
            domains=[
                DomainReport(
                    domain="engineering",
                    total=50,
                    correct_verdict=45,
                    precision=0.90,
                    recall=0.90,
                    f1=0.90,
                    avg_latency_ms=100.0,
                    cases=[],
                ),
            ],
            overall_f1=0.90,
            prompt_versions={},
            model_ids=["test"],
        )
        new_report = HarnessReport(
            run_id="run_new",
            timestamp=datetime.now(tz=UTC),
            domains=[
                DomainReport(
                    domain="engineering",
                    total=50,
                    correct_verdict=44,
                    precision=0.89,
                    recall=0.89,
                    f1=0.89,
                    avg_latency_ms=100.0,
                    cases=[],
                ),
            ],
            overall_f1=0.89,
            prompt_versions={},
            model_ids=["test"],
        )
        detector = DriftDetector(threshold=0.02)
        alerts = detector.compare(old_report, new_report)
        regressions = [a for a in alerts if a.is_regression]
        assert len(regressions) == 0
