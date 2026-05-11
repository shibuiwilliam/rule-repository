"""Structured constraint models for deterministic evaluation.

Constraints are stored on rules as structured data (not parsed from free text).
Each constraint represents a single verifiable condition that can be checked
against subject data without calling the LLM.

See IMPROVEMENT.md Proposal 9.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime


class Operator(str, enum.Enum):
    """Comparison operators for numeric and date constraints."""

    LT = "<"
    LE = "<="
    EQ = "=="
    GE = ">="
    GT = ">"
    NE = "!="


class DeterministicVerdict(str, enum.Enum):
    """Result of a deterministic constraint check.

    PASS: all constraints satisfied — no LLM call needed for this rule.
    FAIL: one or more constraints violated — rule is DENY without LLM.
    INDETERMINATE: constraints exist but cannot be evaluated against
        available data — fall through to LLM.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class NumericConstraint:
    """A numeric comparison constraint.

    Args:
        field_path: Dot-separated path into the subject's facts dict
            (e.g. ``"amount"``, ``"per_person_entertainment"``, ``"hours"``).
        operator: Comparison operator.
        threshold: The boundary value.
        unit: Optional unit label for human-readable messages
            (e.g. ``"JPY"``, ``"hours"``, ``"%"``).
    """

    field_path: str
    operator: Operator
    threshold: float
    unit: str = ""

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for storage."""
        return {
            "type": "numeric",
            "field_path": self.field_path,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NumericConstraint:
        """Deserialize from a stored dict."""
        return cls(
            field_path=data["field_path"],
            operator=Operator(data["operator"]),
            threshold=float(data["threshold"]),
            unit=data.get("unit", ""),
        )


@dataclass(frozen=True)
class DateConstraint:
    """A date comparison constraint.

    Args:
        field_path: Dot-separated path into the subject's facts dict.
        operator: Comparison operator (applied to dates).
        reference_date: The boundary date.
    """

    field_path: str
    operator: Operator
    reference_date: datetime

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for storage."""
        return {
            "type": "date",
            "field_path": self.field_path,
            "operator": self.operator.value,
            "reference_date": self.reference_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> DateConstraint:
        """Deserialize from a stored dict."""
        return cls(
            field_path=data["field_path"],
            operator=Operator(data["operator"]),
            reference_date=datetime.fromisoformat(data["reference_date"]),
        )


@dataclass(frozen=True)
class EnumConstraint:
    """An enumeration / allowed-values constraint.

    Args:
        field_path: Dot-separated path into the subject's facts dict.
        allowed_values: Set of acceptable values.
    """

    field_path: str
    allowed_values: frozenset[str]

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for storage."""
        return {
            "type": "enum",
            "field_path": self.field_path,
            "allowed_values": sorted(self.allowed_values),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EnumConstraint:
        """Deserialize from a stored dict."""
        return cls(
            field_path=data["field_path"],
            allowed_values=frozenset(data["allowed_values"]),
        )


# Union type for any constraint kind.
Constraint = NumericConstraint | DateConstraint | EnumConstraint


def constraint_from_dict(data: dict) -> Constraint:
    """Deserialize a constraint from a stored dict.

    Args:
        data: Dict with a ``type`` key indicating the constraint kind.

    Returns:
        The appropriate constraint instance.

    Raises:
        ValueError: If the ``type`` is unknown.
    """
    ctype = data.get("type", "")
    match ctype:
        case "numeric":
            return NumericConstraint.from_dict(data)
        case "date":
            return DateConstraint.from_dict(data)
        case "enum":
            return EnumConstraint.from_dict(data)
        case _:
            msg = f"Unknown constraint type: {ctype!r}"
            raise ValueError(msg)
