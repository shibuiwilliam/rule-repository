"""Tests for the table-driven lookup evaluator."""

from __future__ import annotations

import pytest

from rulerepo_server.services.evaluation.deterministic.lookup_evaluator import (
    clear_lookup_tables,
    evaluate_lookup,
    get_lookup_table,
    register_lookup_table,
)


@pytest.fixture(autouse=True)
def _clean_tables() -> None:
    """Ensure lookup tables are clean before each test."""
    clear_lookup_tables()


class TestRegisterAndGet:
    """Tests for register_lookup_table and get_lookup_table."""

    def test_register_and_retrieve(self) -> None:
        entries = [{"vendor": "Acme"}, {"vendor": "Globex"}]
        register_lookup_table("approved_vendors", entries)
        table = get_lookup_table("approved_vendors")
        assert table is not None
        assert len(table) == 2

    def test_get_nonexistent_returns_none(self) -> None:
        assert get_lookup_table("nonexistent") is None

    def test_clear_removes_all(self) -> None:
        register_lookup_table("t1", [{"a": 1}])
        register_lookup_table("t2", [{"b": 2}])
        clear_lookup_tables()
        assert get_lookup_table("t1") is None
        assert get_lookup_table("t2") is None


class TestEvaluateLookup:
    """Tests for evaluate_lookup."""

    def test_allowlist_value_found(self) -> None:
        register_lookup_table(
            "approved_vendors",
            [{"vendor": "Acme"}, {"vendor": "Globex"}],
        )
        result = evaluate_lookup(
            table_name="approved_vendors",
            lookup_key="vendor",
            lookup_value="Acme",
            must_exist=True,
        )
        assert result.passed is True
        assert len(result.matched_entries) == 1
        assert result.matched_entries[0]["vendor"] == "Acme"

    def test_allowlist_value_not_found(self) -> None:
        register_lookup_table(
            "approved_vendors",
            [{"vendor": "Acme"}, {"vendor": "Globex"}],
        )
        result = evaluate_lookup(
            table_name="approved_vendors",
            lookup_key="vendor",
            lookup_value="Unknown Corp",
            must_exist=True,
        )
        assert result.passed is False
        assert len(result.matched_entries) == 0

    def test_blocklist_value_found(self) -> None:
        register_lookup_table(
            "blocked_vendors",
            [{"vendor": "BadCorp"}],
        )
        result = evaluate_lookup(
            table_name="blocked_vendors",
            lookup_key="vendor",
            lookup_value="BadCorp",
            must_exist=False,
        )
        assert result.passed is False

    def test_blocklist_value_not_found(self) -> None:
        register_lookup_table(
            "blocked_vendors",
            [{"vendor": "BadCorp"}],
        )
        result = evaluate_lookup(
            table_name="blocked_vendors",
            lookup_key="vendor",
            lookup_value="GoodCorp",
            must_exist=False,
        )
        assert result.passed is True

    def test_missing_table_returns_error(self) -> None:
        result = evaluate_lookup(
            table_name="nonexistent",
            lookup_key="vendor",
            lookup_value="Acme",
        )
        assert result.passed is False
        assert result.error is not None
        assert "not found" in result.error

    def test_multiple_matches(self) -> None:
        register_lookup_table(
            "categories",
            [
                {"category": "travel", "limit": 5000},
                {"category": "travel", "limit": 10000},
            ],
        )
        result = evaluate_lookup(
            table_name="categories",
            lookup_key="category",
            lookup_value="travel",
            must_exist=True,
        )
        assert result.passed is True
        assert len(result.matched_entries) == 2

    def test_result_metadata(self) -> None:
        register_lookup_table("t", [{"k": "v"}])
        result = evaluate_lookup(
            table_name="t",
            lookup_key="k",
            lookup_value="v",
        )
        assert result.lookup_table == "t"
        assert result.lookup_key == "k"
        assert result.lookup_value == "v"

    def test_matched_entries_is_tuple(self) -> None:
        register_lookup_table("t", [{"k": "v"}])
        result = evaluate_lookup(
            table_name="t",
            lookup_key="k",
            lookup_value="v",
        )
        assert isinstance(result.matched_entries, tuple)
