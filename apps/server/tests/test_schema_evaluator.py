"""Tests for the schema-based deterministic evaluator."""

from __future__ import annotations

from rulerepo_server.services.evaluation.deterministic.schema_evaluator import (
    evaluate_schema,
)


class TestEvaluateSchema:
    """Tests for evaluate_schema."""

    def test_all_required_fields_present(self) -> None:
        schema_def = {
            "name": {"type": "str", "required": True},
            "amount": {"type": "float", "required": True},
        }
        data = {"name": "Test", "amount": 100.0}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_required_field_missing(self) -> None:
        schema_def = {
            "name": {"type": "str", "required": True},
            "amount": {"type": "float", "required": True},
        }
        data = {"name": "Test"}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is False
        assert any("amount" in e and "missing" in e for e in result.errors)

    def test_optional_field_missing_passes(self) -> None:
        schema_def = {
            "name": {"type": "str", "required": True},
            "notes": {"type": "str", "required": False},
        }
        data = {"name": "Test"}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True

    def test_conditional_required_field_condition_met(self) -> None:
        """receipt_url required when amount >= 3000."""
        schema_def = {
            "receipt_url": {
                "type": "str",
                "required": True,
                "condition": "amount >= 3000",
            },
            "amount": {"type": "float", "required": True},
        }
        data = {"amount": 5000.0}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is False
        assert any("receipt_url" in e for e in result.errors)

    def test_conditional_required_field_condition_not_met(self) -> None:
        """receipt_url not required when amount < 3000."""
        schema_def = {
            "receipt_url": {
                "type": "str",
                "required": True,
                "condition": "amount >= 3000",
            },
            "amount": {"type": "float", "required": True},
        }
        data = {"amount": 1000.0}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True

    def test_conditional_required_field_condition_met_and_present(self) -> None:
        schema_def = {
            "receipt_url": {
                "type": "str",
                "required": True,
                "condition": "amount >= 3000",
            },
            "amount": {"type": "float", "required": True},
        }
        data = {"amount": 5000.0, "receipt_url": "https://example.com/receipt.pdf"}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True

    def test_type_check_passes(self) -> None:
        schema_def = {"count": {"type": "int", "required": True}}
        data = {"count": 42}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True

    def test_type_check_coercible(self) -> None:
        """String '42' is coercible to int, so it passes."""
        schema_def = {"count": {"type": "int", "required": True}}
        data = {"count": "42"}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True

    def test_type_check_fails(self) -> None:
        schema_def = {"count": {"type": "int", "required": True}}
        data = {"count": "not-a-number"}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is False
        assert any("count" in e and "expected int" in e for e in result.errors)

    def test_min_range_check(self) -> None:
        schema_def = {"amount": {"type": "float", "required": True, "min": 0}}
        data = {"amount": -5.0}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is False
        assert any("below minimum" in e for e in result.errors)

    def test_max_range_check(self) -> None:
        schema_def = {"amount": {"type": "float", "required": True, "max": 10000}}
        data = {"amount": 15000.0}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is False
        assert any("exceeds maximum" in e for e in result.errors)

    def test_range_within_bounds(self) -> None:
        schema_def = {
            "amount": {"type": "float", "required": True, "min": 0, "max": 10000},
        }
        data = {"amount": 500.0}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is True

    def test_schema_name_in_result(self) -> None:
        result = evaluate_schema(
            schema_def={},
            data={},
            schema_name="expense_report",
        )
        assert result.schema_name == "expense_report"

    def test_multiple_errors_collected(self) -> None:
        schema_def = {
            "name": {"type": "str", "required": True},
            "email": {"type": "str", "required": True},
            "age": {"type": "int", "required": True},
        }
        data: dict = {}
        result = evaluate_schema(schema_def=schema_def, data=data)
        assert result.passed is False
        assert len(result.errors) == 3

    def test_empty_schema_passes(self) -> None:
        result = evaluate_schema(schema_def={}, data={"anything": "goes"})
        assert result.passed is True

    def test_errors_is_tuple(self) -> None:
        result = evaluate_schema(schema_def={}, data={})
        assert isinstance(result.errors, tuple)
