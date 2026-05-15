"""Tests for the deterministic numeric evaluator and runner."""

from rulerepo_server.domain.rule import (
    ComputationalBody,
    NormativeBody,
    PrincipleBody,
    ProceduralBody,
    RuleKind,
)
from rulerepo_server.services.evaluation.deterministic.numeric_evaluator import (
    evaluate_expression,
)
from rulerepo_server.services.evaluation.deterministic.runner import (
    evaluate_deterministic,
)

# ---------------------------------------------------------------------------
# evaluate_expression tests
# ---------------------------------------------------------------------------


class TestEvaluateExpression:
    """Test the asteval-based expression evaluator."""

    def test_simple_le_pass(self) -> None:
        result = evaluate_expression("x <= 45", {"x": 30})
        assert result.passed is True
        assert result.error is None

    def test_simple_le_fail(self) -> None:
        result = evaluate_expression("x <= 45", {"x": 50})
        assert result.passed is False
        assert result.error is None

    def test_sum_pass(self) -> None:
        result = evaluate_expression("sum(hours) <= 45", {"hours": [10, 20, 10]})
        assert result.passed is True

    def test_sum_fail(self) -> None:
        result = evaluate_expression("sum(hours) <= 45", {"hours": [20, 20, 10]})
        assert result.passed is False

    def test_equality(self) -> None:
        result = evaluate_expression("status == 1", {"status": 1})
        assert result.passed is True

    def test_arithmetic_expression(self) -> None:
        result = evaluate_expression("a + b", {"a": 3, "b": 4})
        assert result.passed is True
        assert result.computed_value == 7

    def test_zero_is_falsy(self) -> None:
        result = evaluate_expression("a - b", {"a": 5, "b": 5})
        assert result.passed is False
        assert result.computed_value == 0

    def test_division_by_zero(self) -> None:
        result = evaluate_expression("x / y", {"x": 10, "y": 0})
        # asteval should report an error for division by zero
        assert result.error is not None
        assert result.passed is False

    def test_missing_variable(self) -> None:
        result = evaluate_expression("unknown_var <= 10", {})
        assert result.error is not None
        assert result.passed is False

    def test_complex_expression(self) -> None:
        result = evaluate_expression(
            "total <= limit and count > 0",
            {"total": 100, "limit": 200, "count": 5},
        )
        assert result.passed is True

    def test_min_max_builtins(self) -> None:
        result = evaluate_expression("max(values) <= 100", {"values": [50, 80, 90]})
        assert result.passed is True

    def test_abs_builtin(self) -> None:
        result = evaluate_expression("abs(diff) < 10", {"diff": -5})
        assert result.passed is True

    def test_len_builtin(self) -> None:
        result = evaluate_expression("len(items) >= 3", {"items": [1, 2, 3, 4]})
        assert result.passed is True


# ---------------------------------------------------------------------------
# evaluate_deterministic runner tests
# ---------------------------------------------------------------------------


class TestDeterministicRunner:
    """Test the rule-kind-dispatched runner."""

    def test_computational_pass(self) -> None:
        body = ComputationalBody(expression="hours <= 45", required_inputs=["hours"])
        verdict = evaluate_deterministic(
            rule_id="r1",
            kind=RuleKind.COMPUTATIONAL,
            body=body,
            inputs={"hours": 30},
        )
        assert verdict.resolved is True
        assert verdict.passed is True
        assert verdict.needs_llm_followup is False

    def test_computational_fail(self) -> None:
        body = ComputationalBody(expression="hours <= 45", required_inputs=["hours"])
        verdict = evaluate_deterministic(
            rule_id="r1",
            kind=RuleKind.COMPUTATIONAL,
            body=body,
            inputs={"hours": 50},
        )
        assert verdict.resolved is True
        assert verdict.passed is False
        assert verdict.needs_llm_followup is False

    def test_computational_with_exception_predicate(self) -> None:
        body = ComputationalBody(
            expression="hours <= 45",
            required_inputs=["hours"],
            exception_predicate="has_36_agreement",
        )
        verdict = evaluate_deterministic(
            rule_id="r1",
            kind=RuleKind.COMPUTATIONAL,
            body=body,
            inputs={"hours": 50},
        )
        # Even though hours > 45, exception_predicate means LLM must check
        assert verdict.resolved is False
        assert verdict.passed is False
        assert verdict.needs_llm_followup is True
        assert "exception applies" in verdict.followup_context

    def test_computational_empty_expression(self) -> None:
        body = ComputationalBody(expression="", required_inputs=[])
        verdict = evaluate_deterministic(
            rule_id="r1",
            kind=RuleKind.COMPUTATIONAL,
            body=body,
            inputs={},
        )
        assert verdict.resolved is False
        assert verdict.needs_llm_followup is True

    def test_normative_with_predicate(self) -> None:
        body = NormativeBody(predicate="amount <= 50000")
        verdict = evaluate_deterministic(
            rule_id="r2",
            kind=RuleKind.NORMATIVE,
            body=body,
            inputs={"amount": 30000},
        )
        # Normative rules always need LLM follow-up even if predicate passes
        assert verdict.resolved is False
        assert verdict.passed is True
        assert verdict.needs_llm_followup is True

    def test_normative_without_predicate(self) -> None:
        body = NormativeBody()
        verdict = evaluate_deterministic(
            rule_id="r2",
            kind=RuleKind.NORMATIVE,
            body=body,
            inputs={},
        )
        assert verdict.resolved is False
        assert verdict.needs_llm_followup is True

    def test_principle_skips_deterministic(self) -> None:
        body = PrincipleBody(guidance="Act in good faith")
        verdict = evaluate_deterministic(
            rule_id="r3",
            kind=RuleKind.PRINCIPLE,
            body=body,
            inputs={},
        )
        assert verdict.resolved is False
        assert verdict.needs_llm_followup is True

    def test_procedural_defers_to_llm(self) -> None:
        body = ProceduralBody(
            states=["draft", "review", "approved"],
            initial_state="draft",
            terminal_states=["approved"],
        )
        verdict = evaluate_deterministic(
            rule_id="r4",
            kind=RuleKind.PROCEDURAL,
            body=body,
            inputs={},
        )
        # Procedural not yet implemented — defers to LLM
        assert verdict.resolved is False
        assert verdict.needs_llm_followup is True

    def test_computational_expression_error(self) -> None:
        body = ComputationalBody(expression="invalid syntax !@#", required_inputs=[])
        verdict = evaluate_deterministic(
            rule_id="r5",
            kind=RuleKind.COMPUTATIONAL,
            body=body,
            inputs={},
        )
        assert verdict.resolved is False
        assert verdict.needs_llm_followup is True
        assert "error" in verdict.followup_context.lower()
