"""Tests for structured scope dimension matching (RR-040)."""

from __future__ import annotations

from rulerepo_server.domain.scope import StructuredScope, matches_scope_dimensions


class TestMatchesScopeDimensions:
    """Test multi-axis scope dimension filtering."""

    def test_empty_query_matches_everything(self) -> None:
        rule = {"jurisdiction": "JP", "business_unit": "finance"}
        assert matches_scope_dimensions(rule, {}) is True

    def test_empty_rule_matches_everything(self) -> None:
        query = {"jurisdiction": "JP"}
        assert matches_scope_dimensions({}, query) is True

    def test_exact_match_single_value(self) -> None:
        rule = {"jurisdiction": "JP"}
        query = {"jurisdiction": "JP"}
        assert matches_scope_dimensions(rule, query) is True

    def test_no_match_different_value(self) -> None:
        rule = {"jurisdiction": "US"}
        query = {"jurisdiction": "JP"}
        assert matches_scope_dimensions(rule, query) is False

    def test_list_overlap(self) -> None:
        rule = {"jurisdiction": ["JP", "US"]}
        query = {"jurisdiction": "JP"}
        assert matches_scope_dimensions(rule, query) is True

    def test_list_no_overlap(self) -> None:
        rule = {"jurisdiction": ["EU", "UK"]}
        query = {"jurisdiction": "JP"}
        assert matches_scope_dimensions(rule, query) is False

    def test_multi_dimension_all_match(self) -> None:
        rule = {"jurisdiction": "JP", "business_unit": "finance"}
        query = {"jurisdiction": "JP", "business_unit": "finance"}
        assert matches_scope_dimensions(rule, query) is True

    def test_multi_dimension_partial_mismatch(self) -> None:
        rule = {"jurisdiction": "JP", "business_unit": "hr"}
        query = {"jurisdiction": "JP", "business_unit": "finance"}
        assert matches_scope_dimensions(rule, query) is False

    def test_rule_missing_dimension_is_wildcard(self) -> None:
        """Rule without a dimension doesn't restrict it."""
        rule = {"jurisdiction": "JP"}
        query = {"jurisdiction": "JP", "confidentiality": "restricted"}
        assert matches_scope_dimensions(rule, query) is True

    def test_query_list_values(self) -> None:
        rule = {"jurisdiction": "JP"}
        query = {"jurisdiction": ["JP", "US"]}
        assert matches_scope_dimensions(rule, query) is True

    def test_structured_scope_dataclass(self) -> None:
        scope = StructuredScope(
            path="legal/contracts",
            dimensions={"jurisdiction": ["JP", "US"], "counterparty_type": "vendor"},
        )
        assert scope.path == "legal/contracts"
        assert "JP" in scope.dimensions["jurisdiction"]
