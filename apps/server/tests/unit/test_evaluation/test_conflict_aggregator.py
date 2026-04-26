"""Unit tests for conflict-aware verdict aggregation."""

from rulerepo_server.domain.evaluation import RuleVerdict, Verdict
from rulerepo_server.services.evaluation.conflict_aggregator import (
    aggregate_with_conflicts,
)
from rulerepo_server.services.evaluation.graph_resolver import EvaluationPlan


def _v(rule_id: str, verdict: Verdict) -> RuleVerdict:
    return RuleVerdict(
        rule_id=rule_id,
        rule_statement=f"Rule {rule_id}",
        verdict=verdict,
        confidence=0.9,
        reasoning="test",
    )


class TestOverrides:
    def test_overridden_verdict_discarded(self) -> None:
        verdicts = [_v("r1", Verdict.DENY), _v("r2", Verdict.ALLOW)]
        plan = EvaluationPlan(
            ordered_rules=["r1", "r2"],
            overrides={"r1": "r2"},  # r2 overrides r1
        )
        rules = {"r1": {"severity": "HIGH"}, "r2": {"severity": "HIGH"}}
        overall, resolutions = aggregate_with_conflicts(verdicts, plan, rules)
        assert overall == Verdict.ALLOW  # r1's DENY was overridden
        assert len(resolutions) == 1
        assert resolutions[0].winner_id == "r2"


class TestConflictsWith:
    def test_higher_severity_wins(self) -> None:
        verdicts = [_v("r1", Verdict.DENY), _v("r2", Verdict.ALLOW)]
        plan = EvaluationPlan(
            ordered_rules=["r1", "r2"],
            conflicts=[("r1", "r2")],
        )
        rules = {
            "r1": {"severity": "CRITICAL", "modality": "MUST", "scope": []},
            "r2": {"severity": "MEDIUM", "modality": "MUST", "scope": []},
        }
        overall, resolutions = aggregate_with_conflicts(verdicts, plan, rules)
        assert overall == Verdict.DENY  # r1 (CRITICAL) wins
        assert resolutions[0].winner_id == "r1"
        assert "severity" in resolutions[0].reason.lower()

    def test_stronger_modality_wins_on_tie(self) -> None:
        verdicts = [_v("r1", Verdict.DENY), _v("r2", Verdict.ALLOW)]
        plan = EvaluationPlan(
            ordered_rules=["r1", "r2"],
            conflicts=[("r1", "r2")],
        )
        rules = {
            "r1": {"severity": "HIGH", "modality": "MUST", "scope": []},
            "r2": {"severity": "HIGH", "modality": "SHOULD", "scope": []},
        }
        overall, resolutions = aggregate_with_conflicts(verdicts, plan, rules)
        assert resolutions[0].winner_id == "r1"
        assert "modality" in resolutions[0].reason.lower()


class TestDependsOn:
    def test_dependent_skipped_on_deny(self) -> None:
        verdicts = [_v("prereq", Verdict.DENY), _v("dep", Verdict.ALLOW)]
        plan = EvaluationPlan(
            ordered_rules=["prereq", "dep"],
            skip_if_denied={"prereq": ["dep"]},
        )
        rules = {"prereq": {}, "dep": {}}
        overall, _ = aggregate_with_conflicts(verdicts, plan, rules)
        assert overall == Verdict.DENY  # prereq DENY stands, dep skipped


class TestNoRelationships:
    def test_standard_aggregation(self) -> None:
        verdicts = [_v("r1", Verdict.ALLOW), _v("r2", Verdict.ALLOW)]
        plan = EvaluationPlan(ordered_rules=["r1", "r2"])
        overall, resolutions = aggregate_with_conflicts(verdicts, plan, {})
        assert overall == Verdict.ALLOW
        assert len(resolutions) == 0
