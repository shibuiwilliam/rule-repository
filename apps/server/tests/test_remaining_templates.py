"""Tests for the remaining Domain Pack templates (PR 4.3).

Validates templates added after the initial three:
  - legal-contracts-en-us (10 rules)
  - hr-conduct (8 rules)
  - finance-procurement (8 rules)
  - sales-pricing-jp (8 rules)
  - communication-marketing-jp (8 rules)

Each template must conform to the schema in CLAUDE.md §14.12:
  - Required fields on every rule
  - Computational rules have a body with expression and required_inputs
  - All templates ship as maturity_level=experimental
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_PACKS_DIR = REPO_ROOT / "packages" / "domain-packs"

TEMPLATE_SPECS: list[tuple[Path, int]] = [
    (DOMAIN_PACKS_DIR / "legal" / "templates" / "legal-contracts-en-us.yaml", 10),
    (DOMAIN_PACKS_DIR / "hr" / "templates" / "hr-conduct.yaml", 8),
    (DOMAIN_PACKS_DIR / "finance" / "templates" / "finance-procurement.yaml", 8),
    (DOMAIN_PACKS_DIR / "sales" / "templates" / "sales-pricing-jp.yaml", 8),
    (DOMAIN_PACKS_DIR / "communication" / "templates" / "communication-marketing-jp.yaml", 8),
]

REQUIRED_RULE_FIELDS = {
    "id",
    "statement",
    "kind",
    "modality",
    "severity",
    "scope",
    "rationale",
    "following_example",
    "violation_example",
    "test_cases",
}

VALID_KINDS = {"normative", "computational", "procedural", "definitional", "principle"}
VALID_MODALITIES = {"MUST", "MUST_NOT", "SHOULD", "SHOULD_NOT", "MAY"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def _load_template(path: Path) -> dict:
    """Load and parse a YAML template file."""
    assert path.exists(), f"Template file not found: {path}"
    with open(path) as f:
        data = yaml.safe_load(f)
    assert data is not None, f"Template file is empty: {path}"
    return data


@pytest.fixture(
    params=TEMPLATE_SPECS,
    ids=lambda spec: spec[0].stem,
)
def template_and_expected_count(request: pytest.FixtureRequest) -> tuple[dict, int]:
    """Parametrized fixture yielding (template_dict, expected_rule_count)."""
    path, expected_count = request.param
    return _load_template(path), expected_count


@pytest.fixture
def template(template_and_expected_count: tuple[dict, int]) -> dict:
    return template_and_expected_count[0]


@pytest.fixture
def expected_count(template_and_expected_count: tuple[dict, int]) -> int:
    return template_and_expected_count[1]


class TestTemplateStructure:
    """Validate top-level template metadata."""

    def test_has_required_top_level_fields(self, template: dict) -> None:
        for field in ("name", "domain", "description", "maturity_level", "language", "rules"):
            assert field in template, f"Missing top-level field: {field}"

    def test_maturity_level_is_experimental(self, template: dict) -> None:
        assert template["maturity_level"] == "experimental"

    def test_has_expected_number_of_rules(self, template: dict, expected_count: int) -> None:
        assert len(template["rules"]) == expected_count, (
            f"Expected {expected_count} rules, got {len(template['rules'])} in {template['name']}"
        )

    def test_domain_matches_known_domain(self, template: dict) -> None:
        assert template["domain"] in ("legal", "hr", "finance", "sales", "communication", "engineering")


class TestRuleFields:
    """Validate individual rule schemas."""

    @staticmethod
    def _all_rules(template: dict) -> list[tuple[str, dict]]:
        return [(r["id"], r) for r in template["rules"]]

    def test_required_fields_present(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            missing = REQUIRED_RULE_FIELDS - set(rule.keys())
            assert not missing, f"Rule {rule_id} missing fields: {missing}"

    def test_kind_is_valid(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            assert rule["kind"] in VALID_KINDS, f"Rule {rule_id} has invalid kind: {rule['kind']}"

    def test_modality_is_valid(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            assert rule["modality"] in VALID_MODALITIES, f"Rule {rule_id} has invalid modality: {rule['modality']}"

    def test_severity_is_valid(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            assert rule["severity"] in VALID_SEVERITIES, f"Rule {rule_id} has invalid severity: {rule['severity']}"

    def test_scope_is_structured(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            scope = rule["scope"]
            assert isinstance(scope, dict), f"Rule {rule_id} scope must be a dict, got {type(scope).__name__}"
            assert "domain" in scope, f"Rule {rule_id} scope missing 'domain'"

    def test_test_cases_non_empty(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            cases = rule["test_cases"]
            assert isinstance(cases, list) and len(cases) >= 1, f"Rule {rule_id} must have at least one test case"
            for i, tc in enumerate(cases):
                assert "input" in tc, f"Rule {rule_id} test_case[{i}] missing 'input'"
                assert "expected_verdict" in tc, f"Rule {rule_id} test_case[{i}] missing 'expected_verdict'"

    def test_unique_rule_ids(self, template: dict) -> None:
        ids = [r["id"] for r in template["rules"]]
        assert len(ids) == len(set(ids)), f"Duplicate rule IDs in {template['name']}"

    def test_following_and_violation_examples_present(self, template: dict) -> None:
        for rule_id, rule in self._all_rules(template):
            assert rule.get("following_example"), f"Rule {rule_id} must have a non-empty 'following_example'"
            assert rule.get("violation_example"), f"Rule {rule_id} must have a non-empty 'violation_example'"


class TestComputationalRules:
    """Validate that computational rules have the required body structure."""

    def test_computational_rules_have_body(self, template: dict) -> None:
        computational = [r for r in template["rules"] if r["kind"] == "computational"]
        for rule in computational:
            assert "body" in rule, f"Computational rule {rule['id']} must have a 'body' field"
            body = rule["body"]
            assert "expression" in body, f"Computational rule {rule['id']} body must have 'expression'"
            assert "required_inputs" in body, f"Computational rule {rule['id']} body must have 'required_inputs'"
            assert isinstance(body["required_inputs"], list), (
                f"Computational rule {rule['id']} body.required_inputs must be a list"
            )
            assert len(body["required_inputs"]) >= 1, (
                f"Computational rule {rule['id']} must have at least one required input"
            )

    def test_required_input_fields(self, template: dict) -> None:
        computational = [r for r in template["rules"] if r["kind"] == "computational"]
        for rule in computational:
            if "body" not in rule:
                continue
            for inp in rule["body"]["required_inputs"]:
                assert "name" in inp, f"Computational rule {rule['id']}: required_input missing 'name'"
                assert "type" in inp, f"Computational rule {rule['id']}: required_input missing 'type'"


class TestDomainSpecificConstraints:
    """Validate domain-specific expectations per CLAUDE.md §14.12."""

    def test_hr_conduct_has_computational_gift_rule(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "hr" / "templates" / "hr-conduct.yaml")
        computational = [r for r in template["rules"] if r["kind"] == "computational"]
        assert len(computational) >= 1, "HR conduct template should have at least 1 computational rule (gift limit)"

    def test_finance_procurement_has_computational_rules(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "finance" / "templates" / "finance-procurement.yaml")
        computational = [r for r in template["rules"] if r["kind"] == "computational"]
        assert len(computational) >= 2, (
            f"Finance procurement template should have at least 2 computational rules, got {len(computational)}"
        )

    def test_sales_pricing_has_computational_rules(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "sales" / "templates" / "sales-pricing-jp.yaml")
        computational = [r for r in template["rules"] if r["kind"] == "computational"]
        assert len(computational) >= 2, (
            f"Sales pricing template should have at least 2 computational rules, got {len(computational)}"
        )

    def test_communication_marketing_has_computational_rule(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "communication" / "templates" / "communication-marketing-jp.yaml")
        computational = [r for r in template["rules"] if r["kind"] == "computational"]
        assert len(computational) >= 1, (
            "Communication marketing template should have at least 1 computational rule (prize limit)"
        )

    def test_legal_en_us_language_is_en(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "legal" / "templates" / "legal-contracts-en-us.yaml")
        assert template["language"] == "en"

    def test_legal_en_us_jurisdiction_is_us(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "legal" / "templates" / "legal-contracts-en-us.yaml")
        for rule in template["rules"]:
            attrs = rule["scope"].get("attributes", {})
            assert attrs.get("jurisdiction") == "US", f"Rule {rule['id']} should have jurisdiction=US"

    def test_sales_pricing_language_is_ja(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "sales" / "templates" / "sales-pricing-jp.yaml")
        assert template["language"] == "ja"

    def test_communication_marketing_language_is_ja(self) -> None:
        template = _load_template(DOMAIN_PACKS_DIR / "communication" / "templates" / "communication-marketing-jp.yaml")
        assert template["language"] == "ja"
