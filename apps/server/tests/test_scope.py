"""Tests for the Scope dataclass (additive structured scope, PROJECT.md §6.2)."""

import pytest

from rulerepo_server.domain.scope import Scope


class TestScopeMatches:
    """Test Scope.matches() with various scenarios."""

    def test_global_scope_matches_everything(self) -> None:
        rule = Scope()
        request = Scope(domain="legal", org_unit="acme/jp", subject_type="contract")
        assert rule.matches(request)

    def test_domain_match(self) -> None:
        rule = Scope(domain="legal")
        assert rule.matches(Scope(domain="legal"))
        assert not rule.matches(Scope(domain="hr"))

    def test_domain_none_matches_any_domain(self) -> None:
        rule = Scope(domain=None)
        assert rule.matches(Scope(domain="legal"))
        assert rule.matches(Scope(domain="engineering"))

    def test_org_unit_exact_match(self) -> None:
        rule = Scope(org_unit="acme/jp")
        assert rule.matches(Scope(org_unit="acme/jp"))

    def test_org_unit_ancestor_match(self) -> None:
        rule = Scope(org_unit="acme")
        assert rule.matches(Scope(org_unit="acme/jp/sales"))
        assert rule.matches(Scope(org_unit="acme/us"))

    def test_org_unit_no_false_prefix_match(self) -> None:
        """'acme' should not match 'acme2'."""
        rule = Scope(org_unit="acme")
        assert not rule.matches(Scope(org_unit="acme2"))

    def test_org_unit_rule_set_request_none(self) -> None:
        rule = Scope(org_unit="acme")
        assert not rule.matches(Scope(org_unit=None))

    def test_org_unit_none_matches_any(self) -> None:
        rule = Scope(org_unit=None)
        assert rule.matches(Scope(org_unit="acme/jp"))
        assert rule.matches(Scope(org_unit=None))

    def test_subject_type_match(self) -> None:
        rule = Scope(subject_type="contract")
        assert rule.matches(Scope(subject_type="contract"))
        assert not rule.matches(Scope(subject_type="expense"))

    def test_subject_type_none_matches_any(self) -> None:
        rule = Scope(subject_type=None)
        assert rule.matches(Scope(subject_type="contract"))

    def test_attributes_match(self) -> None:
        rule = Scope(attributes={"jurisdiction": "JP"})
        assert rule.matches(Scope(attributes={"jurisdiction": "JP", "role": "manager"}))

    def test_attributes_mismatch(self) -> None:
        rule = Scope(attributes={"jurisdiction": "JP"})
        assert not rule.matches(Scope(attributes={"jurisdiction": "US"}))

    def test_attributes_missing_in_request(self) -> None:
        rule = Scope(attributes={"jurisdiction": "JP"})
        assert not rule.matches(Scope(attributes={}))

    def test_combined_scope_match(self) -> None:
        rule = Scope(
            domain="finance",
            org_unit="acme/jp",
            subject_type="expense",
            attributes={"jurisdiction": "JP"},
        )
        request = Scope(
            domain="finance",
            org_unit="acme/jp/sales",
            subject_type="expense",
            attributes={"jurisdiction": "JP", "role": "manager"},
        )
        assert rule.matches(request)

    def test_combined_scope_domain_mismatch(self) -> None:
        rule = Scope(domain="finance", org_unit="acme")
        request = Scope(domain="legal", org_unit="acme/jp")
        assert not rule.matches(request)


class TestScopeFromLegacyString:
    """Test Scope.from_legacy_string() normalizations."""

    def test_empty_string(self) -> None:
        scope = Scope.from_legacy_string("")
        assert scope == Scope()

    def test_domain_only(self) -> None:
        scope = Scope.from_legacy_string("engineering")
        assert scope.domain == "engineering"
        assert scope.subject_type is None

    def test_domain_and_subject(self) -> None:
        scope = Scope.from_legacy_string("engineering/python")
        assert scope.domain == "engineering"
        assert scope.subject_type == "python_source"

    def test_python_alias(self) -> None:
        scope = Scope.from_legacy_string("engineering/py")
        assert scope.subject_type == "python_source"

    def test_typescript_alias(self) -> None:
        scope = Scope.from_legacy_string("engineering/ts")
        assert scope.subject_type == "typescript_source"

    def test_typescript_full(self) -> None:
        scope = Scope.from_legacy_string("engineering/typescript")
        assert scope.subject_type == "typescript_source"

    def test_react(self) -> None:
        scope = Scope.from_legacy_string("engineering/react")
        assert scope.subject_type == "react_component"

    def test_non_engineering_passthrough(self) -> None:
        scope = Scope.from_legacy_string("legal/contract")
        assert scope.domain == "legal"
        assert scope.subject_type == "contract"

    def test_strips_slashes(self) -> None:
        scope = Scope.from_legacy_string("/engineering/python/")
        assert scope.domain == "engineering"
        assert scope.subject_type == "python_source"


class TestScopeSerialization:
    """Test to_dict / from_dict round-trip."""

    def test_full_round_trip(self) -> None:
        original = Scope(
            domain="finance",
            org_unit="acme/jp",
            subject_type="expense",
            attributes={"jurisdiction": "JP", "confidentiality": "restricted"},
        )
        d = original.to_dict()
        restored = Scope.from_dict(d)
        assert restored == original

    def test_empty_scope_round_trip(self) -> None:
        original = Scope()
        d = original.to_dict()
        assert d == {}
        restored = Scope.from_dict(d)
        assert restored == original

    def test_partial_scope_round_trip(self) -> None:
        original = Scope(domain="hr")
        d = original.to_dict()
        assert d == {"domain": "hr"}
        restored = Scope.from_dict(d)
        assert restored == original

    def test_to_dict_omits_none_fields(self) -> None:
        scope = Scope(domain="legal")
        d = scope.to_dict()
        assert "org_unit" not in d
        assert "subject_type" not in d
        assert "attributes" not in d

    def test_to_dict_omits_empty_attributes(self) -> None:
        scope = Scope(domain="legal", attributes={})
        d = scope.to_dict()
        assert "attributes" not in d

    def test_frozen(self) -> None:
        scope = Scope(domain="legal")
        with pytest.raises(AttributeError):
            scope.domain = "hr"  # type: ignore[misc]
