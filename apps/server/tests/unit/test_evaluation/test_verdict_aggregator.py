"""Unit tests for the verdict aggregator."""

from rulerepo_server.domain.evaluation import RuleVerdict, Verdict
from rulerepo_server.services.evaluation.verdict_aggregator import (
    aggregate_verdicts,
)


def _make_verdict(verdict: Verdict, rule_id: str = "r1", fix: str | None = None) -> RuleVerdict:
    return RuleVerdict(
        rule_id=rule_id,
        rule_statement=f"Test rule {rule_id}",
        verdict=verdict,
        confidence=0.9,
        reasoning="Test reasoning",
        issue_description="Issue" if verdict != Verdict.ALLOW else "",
        fix_suggestion=fix,
    )


class TestAggregateVerdicts:
    def test_all_allow(self) -> None:
        verdicts = [_make_verdict(Verdict.ALLOW, f"r{i}") for i in range(3)]
        result = aggregate_verdicts(verdicts, ["flash"], 100)
        assert result.overall_verdict == Verdict.ALLOW
        assert result.rules_passed == 3
        assert result.rules_violated == 0

    def test_any_deny_means_overall_deny(self) -> None:
        verdicts = [
            _make_verdict(Verdict.ALLOW, "r1"),
            _make_verdict(Verdict.DENY, "r2", fix="Fix this"),
            _make_verdict(Verdict.ALLOW, "r3"),
        ]
        result = aggregate_verdicts(verdicts, ["flash"], 200)
        assert result.overall_verdict == Verdict.DENY
        assert result.rules_violated == 1
        assert result.rules_passed == 2

    def test_needs_confirmation_without_deny(self) -> None:
        verdicts = [
            _make_verdict(Verdict.ALLOW, "r1"),
            _make_verdict(Verdict.NEEDS_CONFIRMATION, "r2"),
        ]
        result = aggregate_verdicts(verdicts, ["flash"], 150)
        assert result.overall_verdict == Verdict.NEEDS_CONFIRMATION
        assert result.rules_uncertain == 1

    def test_deny_overrides_needs_confirmation(self) -> None:
        verdicts = [
            _make_verdict(Verdict.NEEDS_CONFIRMATION, "r1"),
            _make_verdict(Verdict.DENY, "r2", fix="Fix r2"),
        ]
        result = aggregate_verdicts(verdicts, ["flash", "pro"], 300)
        assert result.overall_verdict == Verdict.DENY

    def test_empty_verdicts(self) -> None:
        result = aggregate_verdicts([], [], 0)
        assert result.overall_verdict == Verdict.ALLOW
        assert result.rules_evaluated == 0

    def test_fix_summary_includes_violations(self) -> None:
        verdicts = [
            _make_verdict(Verdict.DENY, "r1", fix="Add validation"),
            _make_verdict(Verdict.DENY, "r2", fix="Add logging"),
        ]
        result = aggregate_verdicts(verdicts, ["flash"], 200)
        assert result.fix_summary is not None
        assert "Add validation" in result.fix_summary
        assert "Add logging" in result.fix_summary

    def test_violations_property(self) -> None:
        verdicts = [
            _make_verdict(Verdict.ALLOW, "r1"),
            _make_verdict(Verdict.DENY, "r2"),
            _make_verdict(Verdict.NEEDS_CONFIRMATION, "r3"),
        ]
        result = aggregate_verdicts(verdicts, ["flash"], 100)
        assert len(result.violations) == 1
        assert len(result.warnings) == 1

    def test_model_ids_deduped(self) -> None:
        result = aggregate_verdicts(
            [_make_verdict(Verdict.ALLOW)],
            ["flash", "flash", "pro"],
            100,
        )
        assert len(result.model_ids_used) == 2
