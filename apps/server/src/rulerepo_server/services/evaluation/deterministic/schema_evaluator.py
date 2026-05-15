"""Schema-based deterministic evaluator using Pydantic.

Validates that a subject's data conforms to a schema predicate
defined in the rule body. Used for rules like "expense reports
must include receipt_url when amount >= 3000".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SchemaResult:
    """Result of a schema validation check."""

    passed: bool
    errors: tuple[str, ...] = ()
    schema_name: str = ""


def evaluate_schema(
    *,
    schema_def: dict[str, Any],
    data: dict[str, Any],
    schema_name: str = "rule_schema",
) -> SchemaResult:
    """Evaluate data against a schema definition.

    The schema_def is a dict mapping field names to type specifications::

        {
            "receipt_url": {"type": "str", "required": True, "condition": "amount >= 3000"},
            "approver_id": {"type": "str", "required": True},
            "amount": {"type": "float", "required": True, "min": 0},
        }

    Args:
        schema_def: Schema definition from the rule body.
        data: The subject data to validate.
        schema_name: Name for error reporting.

    Returns:
        SchemaResult with pass/fail and error details.
    """
    errors: list[str] = []

    for field_name, field_spec in schema_def.items():
        required = field_spec.get("required", False)
        field_type = field_spec.get("type", "str")
        condition = field_spec.get("condition")
        min_val = field_spec.get("min")
        max_val = field_spec.get("max")

        # Check condition -- if condition is not met, skip this field check
        if condition:
            try:
                if not _evaluate_condition(condition, data):
                    continue
            except Exception as exc:
                logger.warning(
                    "condition_evaluation_error",
                    condition=condition,
                    error=str(exc),
                )
                continue

        value = data.get(field_name)

        # Required field check
        if required and value is None:
            errors.append(f"Required field '{field_name}' is missing")
            continue

        if value is None:
            continue

        # Type check
        expected_type = _resolve_type(field_type)
        if expected_type and not isinstance(value, expected_type):
            try:
                expected_type(value)
            except (ValueError, TypeError):
                errors.append(f"Field '{field_name}' has type {type(value).__name__}, expected {field_type}")

        # Range checks
        if min_val is not None and value < min_val:
            errors.append(f"Field '{field_name}' value {value} is below minimum {min_val}")
        if max_val is not None and value > max_val:
            errors.append(f"Field '{field_name}' value {value} exceeds maximum {max_val}")

    return SchemaResult(
        passed=len(errors) == 0,
        errors=tuple(errors),
        schema_name=schema_name,
    )


def _resolve_type(type_name: str) -> type | None:
    """Resolve a type name string to a Python type."""
    type_map: dict[str, type] = {
        "str": str,
        "string": str,
        "int": int,
        "integer": int,
        "float": float,
        "number": float,
        "bool": bool,
        "boolean": bool,
        "list": list,
        "dict": dict,
    }
    return type_map.get(type_name.lower())


def _evaluate_condition(condition: str, data: dict[str, Any]) -> bool:
    """Evaluate a simple condition against data.

    Supports: ``field >= value``, ``field <= value``, ``field == value``,
    ``field != value``, ``field > value``, ``field < value``.
    """
    match = re.match(r"(\w+)\s*(>=|<=|==|!=|>|<)\s*(.+)", condition.strip())
    if not match:
        return True  # Unparseable condition -- skip

    field, op, value_str = match.groups()
    field_val = data.get(field)
    if field_val is None:
        return False

    try:
        target = type(field_val)(value_str)
    except (ValueError, TypeError):
        return True

    ops: dict[str, Any] = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    return ops[op](field_val, target)
