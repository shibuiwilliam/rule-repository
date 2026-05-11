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


class TestStructuredScopePrimaryAxes:
    """Test the primary-axis convenience properties and factory methods."""

    def test_domain_property(self) -> None:
        scope = StructuredScope(dimensions={"domain": "finance"})
        assert scope.domain == "finance"

    def test_domain_property_list(self) -> None:
        scope = StructuredScope(dimensions={"domain": ["finance", "legal"]})
        assert scope.domain == "finance"

    def test_domain_property_missing(self) -> None:
        scope = StructuredScope(dimensions={})
        assert scope.domain is None

    def test_org_unit_property(self) -> None:
        scope = StructuredScope(dimensions={"org_unit": "acme/us/sales"})
        assert scope.org_unit == "acme/us/sales"

    def test_subject_type_property(self) -> None:
        scope = StructuredScope(dimensions={"subject_type": "expense"})
        assert scope.subject_type == "expense"

    def test_attributes_excludes_primary_keys(self) -> None:
        scope = StructuredScope(
            dimensions={
                "domain": "finance",
                "org_unit": "acme/us",
                "subject_type": "expense",
                "role": "manager",
                "jurisdiction": "US",
            }
        )
        attrs = scope.attributes
        assert "domain" not in attrs
        assert "org_unit" not in attrs
        assert "subject_type" not in attrs
        assert attrs == {"role": "manager", "jurisdiction": "US"}

    def test_from_legacy_two_segments(self) -> None:
        scope = StructuredScope.from_legacy(["engineering", "python"])
        assert scope.path == "engineering/python"
        assert scope.domain == "engineering"
        assert scope.subject_type == "python"

    def test_from_legacy_single_segment(self) -> None:
        scope = StructuredScope.from_legacy(["legal"])
        assert scope.path == "legal"
        assert scope.domain == "legal"
        assert scope.subject_type is None

    def test_from_legacy_empty(self) -> None:
        scope = StructuredScope.from_legacy([])
        assert scope.path == ""
        assert scope.domain is None

    def test_to_es_fields(self) -> None:
        scope = StructuredScope(
            path="finance/expense",
            dimensions={
                "domain": "finance",
                "org_unit": "acme/us",
                "subject_type": "expense",
                "role": "manager",
            },
        )
        fields = scope.to_es_fields()
        assert fields["scope_domain"] == "finance"
        assert fields["scope_org_unit"] == "acme/us"
        assert fields["scope_subject_type"] == "expense"
        assert fields["scope_dimensions"]["role"] == "manager"


class TestCrossAxisScoping:
    """Test complex cross-organizational scope scenarios from IMPROVEMENT.md §2.2."""

    def test_us_managers_expense_policy(self) -> None:
        """'US managers' expense policy' must match a rule scoped to
        domain=finance, org_unit=acme/us, subject_type=expense, role=manager.
        """
        rule_dims = {
            "domain": "finance",
            "org_unit": "acme/us",
            "subject_type": "expense",
            "role": "manager",
        }
        query = {
            "domain": "finance",
            "org_unit": "acme/us",
            "subject_type": "expense",
            "role": "manager",
        }
        assert matches_scope_dimensions(rule_dims, query) is True

    def test_us_managers_expense_rejected_for_wrong_role(self) -> None:
        rule_dims = {
            "domain": "finance",
            "org_unit": "acme/us",
            "subject_type": "expense",
            "role": "manager",
        }
        query = {
            "domain": "finance",
            "org_unit": "acme/us",
            "subject_type": "expense",
            "role": "intern",
        }
        assert matches_scope_dimensions(rule_dims, query) is False

    def test_cross_domain_legal_rule_matches_finance_query_when_unrestricted(self) -> None:
        """A legal rule without domain restriction matches a finance query."""
        rule_dims = {"jurisdiction": "JP"}
        query = {"domain": "finance", "jurisdiction": "JP"}
        assert matches_scope_dimensions(rule_dims, query) is True

    def test_multi_jurisdiction_rule(self) -> None:
        """A rule applying to JP and US matches a JP-only query."""
        rule_dims = {
            "domain": "hr",
            "jurisdiction": ["JP", "US"],
            "subject_type": "attendance",
        }
        query = {
            "domain": "hr",
            "jurisdiction": "JP",
            "subject_type": "attendance",
        }
        assert matches_scope_dimensions(rule_dims, query) is True

    def test_multi_jurisdiction_rule_rejected_for_eu(self) -> None:
        rule_dims = {
            "domain": "hr",
            "jurisdiction": ["JP", "US"],
        }
        query = {
            "domain": "hr",
            "jurisdiction": "EU",
        }
        assert matches_scope_dimensions(rule_dims, query) is False

    def test_org_unit_hierarchy_exact_match(self) -> None:
        """Exact org_unit match."""
        rule_dims = {"domain": "sales", "org_unit": "acme/jp/sales"}
        query = {"domain": "sales", "org_unit": "acme/jp/sales"}
        assert matches_scope_dimensions(rule_dims, query) is True

    def test_org_unit_hierarchy_different_unit(self) -> None:
        """Different org_unit does not match."""
        rule_dims = {"domain": "sales", "org_unit": "acme/jp/sales"}
        query = {"domain": "sales", "org_unit": "acme/us/sales"}
        assert matches_scope_dimensions(rule_dims, query) is False

    def test_wildcard_rule_matches_any_domain(self) -> None:
        """A rule with no domain restriction matches all domains."""
        rule_dims: dict[str, str | list[str]] = {}
        query = {"domain": "legal", "subject_type": "contract"}
        assert matches_scope_dimensions(rule_dims, query) is True

    def test_full_cross_org_scenario(self) -> None:
        """Complete scenario: contract rule for JP legal department,
        vendor counterparty, confidential.
        """
        rule_dims = {
            "domain": "legal",
            "org_unit": "acme/jp/legal",
            "subject_type": "contract",
            "jurisdiction": "JP",
            "counterparty_type": "vendor",
            "confidentiality": "confidential",
        }
        query = {
            "domain": "legal",
            "org_unit": "acme/jp/legal",
            "subject_type": "contract",
            "jurisdiction": "JP",
            "counterparty_type": "vendor",
            "confidentiality": "confidential",
        }
        assert matches_scope_dimensions(rule_dims, query) is True

        # Same query but different counterparty type should fail
        query_wrong = {**query, "counterparty_type": "partner"}
        assert matches_scope_dimensions(rule_dims, query_wrong) is False
