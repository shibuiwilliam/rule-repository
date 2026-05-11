"""Tests for the deterministic evaluation layer.

Validates the constraint models, serialization, and the DeterministicEvaluator
against numeric, date, and enum constraints.

See IMPROVEMENT.md Proposal 9.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rulerepo_server.services.evaluation.deterministic.constraint import (
    DateConstraint,
    DeterministicVerdict,
    EnumConstraint,
    NumericConstraint,
    Operator,
    constraint_from_dict,
)
from rulerepo_server.services.evaluation.deterministic.evaluator import (
    DeterministicEvaluator,
    EvaluationOutcome,
    _resolve_path,
)


class TestNumericConstraint:
    """Test NumericConstraint creation, serialization, and deserialization."""

    def test_create(self) -> None:
        c = NumericConstraint(field_path="amount", operator=Operator.LE, threshold=100000, unit="JPY")
        assert c.field_path == "amount"
        assert c.operator == Operator.LE
        assert c.threshold == 100000
        assert c.unit == "JPY"

    def test_roundtrip(self) -> None:
        c = NumericConstraint(field_path="hours", operator=Operator.LE, threshold=45, unit="hours")
        d = c.to_dict()
        assert d["type"] == "numeric"
        assert d["threshold"] == 45
        restored = NumericConstraint.from_dict(d)
        assert restored == c

    def test_from_dict_via_factory(self) -> None:
        d = {"type": "numeric", "field_path": "rate", "operator": "<=", "threshold": 15.0, "unit": "%"}
        c = constraint_from_dict(d)
        assert isinstance(c, NumericConstraint)
        assert c.threshold == 15.0


class TestDateConstraint:
    """Test DateConstraint creation and serialization."""

    def test_roundtrip(self) -> None:
        ref = datetime(2026, 3, 31, tzinfo=UTC)
        c = DateConstraint(field_path="due_date", operator=Operator.LE, reference_date=ref)
        d = c.to_dict()
        assert d["type"] == "date"
        restored = DateConstraint.from_dict(d)
        assert restored.reference_date == ref

    def test_from_dict_via_factory(self) -> None:
        d = {
            "type": "date",
            "field_path": "submission_date",
            "operator": "<=",
            "reference_date": "2026-06-30T00:00:00+00:00",
        }
        c = constraint_from_dict(d)
        assert isinstance(c, DateConstraint)


class TestEnumConstraint:
    """Test EnumConstraint creation and serialization."""

    def test_roundtrip(self) -> None:
        c = EnumConstraint(field_path="category", allowed_values=frozenset({"A", "B", "C"}))
        d = c.to_dict()
        assert d["type"] == "enum"
        assert set(d["allowed_values"]) == {"A", "B", "C"}
        restored = EnumConstraint.from_dict(d)
        assert restored.allowed_values == frozenset({"A", "B", "C"})


class TestConstraintFactory:
    """Test the constraint_from_dict factory function."""

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown constraint type"):
            constraint_from_dict({"type": "unknown"})


class TestResolvePath:
    """Test the dot-separated path resolver."""

    def test_simple_key(self) -> None:
        assert _resolve_path({"amount": 42}, "amount") == 42

    def test_nested_key(self) -> None:
        data = {"line_items": {"total": 100}}
        assert _resolve_path(data, "line_items.total") == 100

    def test_list_index(self) -> None:
        data = {"items": [10, 20, 30]}
        assert _resolve_path(data, "items.1") == 20

    def test_missing_key(self) -> None:
        assert _resolve_path({"a": 1}, "b") is None

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": {"d": 99}}}}
        assert _resolve_path(data, "a.b.c.d") == 99


class TestDeterministicEvaluator:
    """Test the DeterministicEvaluator with various constraint types."""

    def setup_method(self) -> None:
        self.evaluator = DeterministicEvaluator()

    # -- Numeric constraints --

    def test_numeric_pass(self) -> None:
        constraints = [NumericConstraint("amount", Operator.LE, 100000, "JPY")]
        facts = {"amount": 50000}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS
        assert result.confidence >= 0.9

    def test_numeric_fail(self) -> None:
        constraints = [NumericConstraint("amount", Operator.LE, 100000, "JPY")]
        facts = {"amount": 150000}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL
        assert "150000" in result.details[0]

    def test_numeric_field_missing(self) -> None:
        constraints = [NumericConstraint("amount", Operator.LE, 100000, "JPY")]
        facts = {"total": 50000}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.INDETERMINATE

    def test_numeric_ge_pass(self) -> None:
        constraints = [NumericConstraint("rest_period_hours", Operator.GE, 11, "hours")]
        facts = {"rest_period_hours": 12}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS

    def test_numeric_ge_fail(self) -> None:
        constraints = [NumericConstraint("rest_period_hours", Operator.GE, 11, "hours")]
        facts = {"rest_period_hours": 8}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL

    def test_overtime_45_hour_cap_pass(self) -> None:
        """Real-world: monthly overtime <= 45 hours (Article 36)."""
        constraints = [NumericConstraint("monthly_overtime_hours", Operator.LE, 45, "hours")]
        facts = {"monthly_overtime_hours": 40}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS

    def test_overtime_45_hour_cap_fail(self) -> None:
        """Real-world: monthly overtime exceeds 45 hours."""
        constraints = [NumericConstraint("monthly_overtime_hours", Operator.LE, 45, "hours")]
        facts = {"monthly_overtime_hours": 52}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL

    def test_entertainment_expense_cap_fail(self) -> None:
        """Real-world: entertainment per-person exceeds 5000 JPY."""
        constraints = [NumericConstraint("per_person_entertainment", Operator.LE, 5000, "JPY")]
        facts = {"per_person_entertainment": 10500}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL
        assert "10500" in result.details[0]

    def test_multiple_constraints_all_pass(self) -> None:
        constraints = [
            NumericConstraint("amount", Operator.LE, 100000, "JPY"),
            NumericConstraint("items_count", Operator.GE, 1, ""),
        ]
        facts = {"amount": 50000, "items_count": 3}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS

    def test_multiple_constraints_one_fails(self) -> None:
        constraints = [
            NumericConstraint("amount", Operator.LE, 100000, "JPY"),
            NumericConstraint("items_count", Operator.GE, 1, ""),
        ]
        facts = {"amount": 200000, "items_count": 3}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL

    # -- Date constraints --

    def test_date_pass(self) -> None:
        ref = datetime(2026, 6, 30, tzinfo=UTC)
        constraints = [DateConstraint("due_date", Operator.LE, ref)]
        facts = {"due_date": "2026-05-15T00:00:00+00:00"}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS

    def test_date_fail(self) -> None:
        ref = datetime(2026, 6, 30, tzinfo=UTC)
        constraints = [DateConstraint("due_date", Operator.LE, ref)]
        facts = {"due_date": "2026-08-01T00:00:00+00:00"}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL

    def test_date_missing_field(self) -> None:
        ref = datetime(2026, 6, 30, tzinfo=UTC)
        constraints = [DateConstraint("due_date", Operator.LE, ref)]
        facts = {"other_date": "2026-05-15"}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.INDETERMINATE

    # -- Enum constraints --

    def test_enum_pass(self) -> None:
        constraints = [EnumConstraint("category", frozenset({"travel", "meals", "supplies"}))]
        facts = {"category": "travel"}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS

    def test_enum_fail(self) -> None:
        constraints = [EnumConstraint("category", frozenset({"travel", "meals", "supplies"}))]
        facts = {"category": "entertainment"}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.FAIL

    # -- Edge cases --

    def test_empty_constraints(self) -> None:
        result = self.evaluator.evaluate([], {"amount": 100})
        assert result.verdict == DeterministicVerdict.INDETERMINATE

    def test_empty_facts(self) -> None:
        constraints = [NumericConstraint("amount", Operator.LE, 100, "")]
        result = self.evaluator.evaluate(constraints, {})
        assert result.verdict == DeterministicVerdict.INDETERMINATE

    def test_string_numeric_value(self) -> None:
        """Numeric constraint should handle string-encoded numbers."""
        constraints = [NumericConstraint("amount", Operator.LE, 100, "")]
        facts = {"amount": "50"}
        result = self.evaluator.evaluate(constraints, facts)
        assert result.verdict == DeterministicVerdict.PASS

    # -- evaluate_from_dicts --

    def test_evaluate_from_dicts(self) -> None:
        """Test the convenience method that deserializes from stored dicts."""
        dicts = [
            {"type": "numeric", "field_path": "hours", "operator": "<=", "threshold": 45, "unit": "hours"},
            {"type": "numeric", "field_path": "amount", "operator": "<=", "threshold": 100000, "unit": "JPY"},
        ]
        facts = {"hours": 40, "amount": 80000}
        result = self.evaluator.evaluate_from_dicts(dicts, facts)
        assert result.verdict == DeterministicVerdict.PASS

    def test_evaluate_from_dicts_with_invalid_entry(self) -> None:
        """Invalid constraint dicts should be skipped, not crash."""
        dicts = [
            {"type": "unknown_type", "field_path": "x"},
            {"type": "numeric", "field_path": "amount", "operator": "<=", "threshold": 100},
        ]
        facts = {"amount": 50}
        result = self.evaluator.evaluate_from_dicts(dicts, facts)
        assert result.verdict == DeterministicVerdict.PASS


class TestEvaluationOutcome:
    """Test EvaluationOutcome repr."""

    def test_repr(self) -> None:
        o = EvaluationOutcome(verdict=DeterministicVerdict.PASS, details=["ok"], confidence=0.95)
        assert "PASS" in repr(o)
        assert "0.95" in repr(o)
