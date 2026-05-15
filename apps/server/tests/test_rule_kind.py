"""Tests for RuleKind enum and body dataclasses."""

from rulerepo_server.domain.rule import (
    ComputationalBody,
    DefinitionalBody,
    NormativeBody,
    PrincipleBody,
    ProceduralBody,
    Rule,
    RuleKind,
)


class TestRuleKindEnum:
    """Verify RuleKind enum values match PROJECT.md §6.3."""

    def test_normative_value(self) -> None:
        assert RuleKind.NORMATIVE.value == "normative"

    def test_computational_value(self) -> None:
        assert RuleKind.COMPUTATIONAL.value == "computational"

    def test_procedural_value(self) -> None:
        assert RuleKind.PROCEDURAL.value == "procedural"

    def test_definitional_value(self) -> None:
        assert RuleKind.DEFINITIONAL.value == "definitional"

    def test_principle_value(self) -> None:
        assert RuleKind.PRINCIPLE.value == "principle"

    def test_all_kinds_present(self) -> None:
        expected = {"normative", "computational", "procedural", "definitional", "principle"}
        actual = {k.value for k in RuleKind}
        assert actual == expected


class TestBodyDataclasses:
    """Verify body variant construction and defaults."""

    def test_normative_body_defaults(self) -> None:
        body = NormativeBody()
        assert body.predicate is None

    def test_normative_body_with_predicate(self) -> None:
        body = NormativeBody(predicate="amount <= 50000")
        assert body.predicate == "amount <= 50000"

    def test_computational_body_defaults(self) -> None:
        body = ComputationalBody()
        assert body.expression == ""
        assert body.required_inputs == []
        assert body.unit is None
        assert body.exception_predicate is None

    def test_computational_body_full(self) -> None:
        body = ComputationalBody(
            expression="total_hours <= 45",
            required_inputs=["total_hours"],
            unit="hours",
            exception_predicate="has_36_agreement",
        )
        assert body.expression == "total_hours <= 45"
        assert body.required_inputs == ["total_hours"]
        assert body.unit == "hours"
        assert body.exception_predicate == "has_36_agreement"

    def test_procedural_body_defaults(self) -> None:
        body = ProceduralBody()
        assert body.states == []
        assert body.transitions == []
        assert body.initial_state == ""
        assert body.terminal_states == []

    def test_definitional_body_defaults(self) -> None:
        body = DefinitionalBody()
        assert body.term == ""
        assert body.definition == ""
        assert body.lookup_table is None

    def test_principle_body_defaults(self) -> None:
        body = PrincipleBody()
        assert body.guidance == ""
        assert body.derived_rule_ids == []

    def test_bodies_are_frozen(self) -> None:
        body = NormativeBody(predicate="x > 0")
        try:
            body.predicate = "y > 0"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # expected — frozen dataclass


class TestRuleDefaults:
    """Verify Rule defaults for kind and body."""

    def test_default_kind_is_normative(self) -> None:
        rule = Rule(statement="Test rule")
        assert rule.kind == RuleKind.NORMATIVE

    def test_default_body_is_normative_body(self) -> None:
        rule = Rule(statement="Test rule")
        assert isinstance(rule.body, NormativeBody)

    def test_computational_rule(self) -> None:
        body = ComputationalBody(expression="hours <= 45", required_inputs=["hours"])
        rule = Rule(
            statement="Monthly overtime must not exceed 45 hours",
            kind=RuleKind.COMPUTATIONAL,
            body=body,
        )
        assert rule.kind == RuleKind.COMPUTATIONAL
        assert isinstance(rule.body, ComputationalBody)
        assert rule.body.expression == "hours <= 45"

    def test_principle_rule(self) -> None:
        body = PrincipleBody(guidance="Act in good faith in all dealings")
        rule = Rule(
            statement="Good faith principle",
            kind=RuleKind.PRINCIPLE,
            body=body,
        )
        assert rule.kind == RuleKind.PRINCIPLE
        assert isinstance(rule.body, PrincipleBody)
