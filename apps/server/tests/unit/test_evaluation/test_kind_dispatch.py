"""Unit tests for kind-based evaluation dispatch."""

from rulerepo_server.domain.evaluation import EvaluationContext, Verdict
from rulerepo_server.domain.rule import RuleKind
from rulerepo_server.services.evaluation.kind_dispatch import (
    evaluate_local,
    partition_by_kind,
)


def _make_rule(
    rule_id: str = "r1",
    kind: str = "normative",
    statement: str = "Test rule",
    modality: str = "MUST",
    severity: str = "MEDIUM",
) -> dict:
    return {
        "id": rule_id,
        "kind": kind,
        "statement": statement,
        "modality": modality,
        "severity": severity,
    }


def _make_context(**facts: object) -> EvaluationContext:
    return EvaluationContext(facts=dict(facts))


# ---------------------------------------------------------------------------
# partition_by_kind
# ---------------------------------------------------------------------------


class TestPartitionByKind:
    def test_all_normative(self) -> None:
        rules = [_make_rule("r1", "normative"), _make_rule("r2", "normative")]
        llm, local = partition_by_kind(rules)
        assert len(llm) == 2
        assert len(local) == 0

    def test_all_local(self) -> None:
        rules = [
            _make_rule("r1", "computational"),
            _make_rule("r2", "definitional"),
            _make_rule("r3", "principle"),
            _make_rule("r4", "procedural"),
        ]
        llm, local = partition_by_kind(rules)
        assert len(llm) == 0
        assert len(local) == 4

    def test_mixed(self) -> None:
        rules = [
            _make_rule("r1", "normative"),
            _make_rule("r2", "computational"),
            _make_rule("r3", "normative"),
            _make_rule("r4", "principle"),
        ]
        llm, local = partition_by_kind(rules)
        assert [r["id"] for r in llm] == ["r1", "r3"]
        assert [r["id"] for r in local] == ["r2", "r4"]

    def test_unknown_kind_treated_as_normative(self) -> None:
        rules = [_make_rule("r1", "unknown_kind")]
        llm, local = partition_by_kind(rules)
        assert len(llm) == 1
        assert len(local) == 0

    def test_missing_kind_treated_as_normative(self) -> None:
        rules = [{"id": "r1", "statement": "Test"}]
        llm, local = partition_by_kind(rules)
        assert len(llm) == 1
        assert len(local) == 0


# ---------------------------------------------------------------------------
# DEFINITIONAL — always ALLOW
# ---------------------------------------------------------------------------


class TestDefinitionalKind:
    def test_returns_allow(self) -> None:
        rule = _make_rule(kind="definitional", statement="A 'working day' is defined as Monday through Friday.")
        ctx = _make_context()
        verdict, model_id, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.ALLOW
        assert verdict.confidence == 1.0
        assert "definitional" in verdict.reasoning.lower()
        assert model_id == "local/kind-dispatch"


# ---------------------------------------------------------------------------
# PRINCIPLE — always ALLOW with note
# ---------------------------------------------------------------------------


class TestPrincipleKind:
    def test_returns_allow(self) -> None:
        rule = _make_rule(kind="principle", statement="We value transparency in all dealings.")
        ctx = _make_context()
        verdict, model_id, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.ALLOW
        assert verdict.confidence == 1.0
        assert "principle" in verdict.reasoning.lower()


# ---------------------------------------------------------------------------
# COMPUTATIONAL — deterministic check
# ---------------------------------------------------------------------------


class TestComputationalKind:
    def test_deny_when_exceeding_threshold(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Monthly overtime hours MUST NOT exceed 45 hours.",
            modality="MUST_NOT",
        )
        ctx = _make_context(overtime_hours=50)
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY
        assert verdict.confidence >= 0.8
        assert "50" in verdict.reasoning or "50" in (verdict.issue_description or "")

    def test_allow_when_within_threshold(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Monthly overtime hours MUST NOT exceed 45 hours.",
            modality="MUST_NOT",
        )
        ctx = _make_context(overtime_hours=30)
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.ALLOW
        assert verdict.confidence >= 0.8

    def test_needs_confirmation_when_no_matching_facts(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Monthly overtime hours MUST NOT exceed 45 hours.",
            modality="MUST_NOT",
        )
        ctx = _make_context(employee_id="E001")  # no numeric fact matching "hour"
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.NEEDS_CONFIRMATION

    def test_needs_confirmation_when_no_facts(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Annual overtime MUST NOT exceed 720 hours.",
            modality="MUST_NOT",
        )
        ctx = _make_context()
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.NEEDS_CONFIRMATION

    def test_must_below_minimum(self) -> None:
        """MUST modality: fact below threshold should DENY."""
        rule = _make_rule(
            kind="computational",
            statement="Break time MUST be at least 45 minutes.",
            modality="MUST",
        )
        ctx = _make_context(break_minutes=30)
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY

    def test_must_above_minimum(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Break time MUST be at least 45 minutes.",
            modality="MUST",
        )
        ctx = _make_context(break_minutes=60)
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.ALLOW

    def test_jpy_threshold(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Per-person entertainment spending MUST NOT exceed 5,000 JPY.",
            modality="MUST_NOT",
        )
        ctx = _make_context(amount_jpy=6000)
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY

    def test_percentage_threshold(self) -> None:
        rule = _make_rule(
            kind="computational",
            statement="Standard discount rate MUST NOT exceed 15%.",
            modality="MUST_NOT",
        )
        ctx = _make_context(discount_rate=20)
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY


# ---------------------------------------------------------------------------
# PROCEDURAL — ordering constraints
# ---------------------------------------------------------------------------


class TestProceduralKind:
    def test_allow_when_steps_include_preconditions(self) -> None:
        rule = _make_rule(
            kind="procedural",
            statement="Overtime MUST NOT be assigned without a 36 Agreement.",
        )
        rule["preconditions"] = ["36 Agreement filed"]
        ctx = EvaluationContext(facts={"steps": ["36 Agreement filed with LSIO", "Overtime assigned to employee"]})
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.ALLOW

    def test_deny_when_precondition_missing(self) -> None:
        rule = _make_rule(
            kind="procedural",
            statement="Overtime MUST NOT be assigned without a 36 Agreement.",
        )
        rule["preconditions"] = ["36 Agreement filed"]
        ctx = EvaluationContext(facts={"steps": ["Overtime assigned to employee"]})
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY

    def test_needs_confirmation_when_no_steps(self) -> None:
        rule = _make_rule(kind="procedural")
        ctx = _make_context(employee_id="E001")
        verdict, _, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.NEEDS_CONFIRMATION


# ---------------------------------------------------------------------------
# RuleKind enum
# ---------------------------------------------------------------------------


class TestRuleKindEnum:
    def test_all_values(self) -> None:
        assert set(RuleKind) == {
            RuleKind.NORMATIVE,
            RuleKind.COMPUTATIONAL,
            RuleKind.PROCEDURAL,
            RuleKind.DEFINITIONAL,
            RuleKind.PRINCIPLE,
        }

    def test_string_values(self) -> None:
        assert RuleKind.NORMATIVE.value == "normative"
        assert RuleKind.COMPUTATIONAL.value == "computational"
        assert RuleKind.PROCEDURAL.value == "procedural"
        assert RuleKind.DEFINITIONAL.value == "definitional"
        assert RuleKind.PRINCIPLE.value == "principle"

    def test_default_on_rule(self) -> None:
        from rulerepo_server.domain.rule import Rule

        r = Rule()
        assert r.kind == RuleKind.NORMATIVE
