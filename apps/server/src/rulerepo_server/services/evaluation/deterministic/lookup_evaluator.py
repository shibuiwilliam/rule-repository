"""Table-driven lookup evaluator.

Evaluates rules by looking up values in predefined tables.
Used for rules like "vendor must be on the approved vendor list"
or "expense category must be in the allowed categories".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LookupResult:
    """Result of a table lookup check."""

    passed: bool
    matched_entries: tuple[dict[str, Any], ...] = ()
    lookup_table: str = ""
    lookup_key: str = ""
    lookup_value: Any = None
    error: str | None = None


# In-memory lookup tables (in production, loaded from a data source)
_LOOKUP_TABLES: dict[str, list[dict[str, Any]]] = {}


def register_lookup_table(name: str, entries: list[dict[str, Any]]) -> None:
    """Register a lookup table for use in evaluations."""
    _LOOKUP_TABLES[name] = entries
    logger.info("lookup_table_registered", name=name, entries=len(entries))


def get_lookup_table(name: str) -> list[dict[str, Any]] | None:
    """Get a registered lookup table by name."""
    return _LOOKUP_TABLES.get(name)


def clear_lookup_tables() -> None:
    """Clear all registered lookup tables (for testing)."""
    _LOOKUP_TABLES.clear()


def evaluate_lookup(
    *,
    table_name: str,
    lookup_key: str,
    lookup_value: Any,
    must_exist: bool = True,
) -> LookupResult:
    """Check whether a value exists in a lookup table.

    Args:
        table_name: Name of the registered lookup table.
        lookup_key: Field name to search in the table entries.
        lookup_value: Value to look for.
        must_exist: If ``True``, the value must be found (allowlist).
                    If ``False``, the value must NOT be found (blocklist).

    Returns:
        LookupResult with pass/fail and matched entries.
    """
    table = _LOOKUP_TABLES.get(table_name)
    if table is None:
        return LookupResult(
            passed=False,
            lookup_table=table_name,
            lookup_key=lookup_key,
            lookup_value=lookup_value,
            error=f"Lookup table '{table_name}' not found",
        )

    matched = [entry for entry in table if entry.get(lookup_key) == lookup_value]

    passed = len(matched) > 0 if must_exist else len(matched) == 0

    return LookupResult(
        passed=passed,
        matched_entries=tuple(matched),
        lookup_table=table_name,
        lookup_key=lookup_key,
        lookup_value=lookup_value,
    )
