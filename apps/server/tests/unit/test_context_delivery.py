"""Unit tests for context delivery formatter and scope registry."""

from rulerepo_server.services.context_delivery.formatter import format_rules

SAMPLE_RULES = [
    {
        "id": "abc12345-1111",
        "statement": "All API handlers must validate input with Pydantic models",
        "modality": "MUST",
        "severity": "HIGH",
        "scope": ["engineering/python"],
        "tags": ["api", "validation"],
        "rationale": "Prevents type errors at API boundaries",
    },
    {
        "id": "abc12345-2222",
        "statement": "Never log full credit card numbers",
        "modality": "MUST_NOT",
        "severity": "CRITICAL",
        "scope": ["engineering"],
        "tags": ["security", "pii"],
        "rationale": "PCI compliance requirement",
    },
    {
        "id": "abc12345-3333",
        "statement": "Use PaymentResult enum for return types",
        "modality": "SHOULD",
        "severity": "MEDIUM",
        "scope": ["engineering/python"],
        "tags": ["api"],
        "rationale": "Consistency across payment handlers",
    },
]


class TestFormatInstructions:
    def test_groups_by_modality(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="instructions")
        assert "### MUST" in result
        assert "### SHOULD" in result

    def test_includes_rule_ids(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="instructions")
        assert "[Rule #abc12345" in result

    def test_includes_context_label(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="instructions", context_label="payment.py")
        assert "payment.py" in result

    def test_must_not_prefix(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="instructions")
        assert "Never:" in result

    def test_empty_rules(self) -> None:
        result = format_rules([], context_label="test")
        assert "No applicable rules" in result


class TestFormatChecklist:
    def test_has_checkboxes(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="checklist")
        assert "- [ ]" in result

    def test_includes_severity(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="checklist")
        assert "[HIGH]" in result
        assert "[CRITICAL]" in result


class TestFormatDetailed:
    def test_includes_rationale(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="detailed")
        assert "Rationale" in result
        assert "PCI compliance" in result

    def test_includes_scope(self) -> None:
        result = format_rules(SAMPLE_RULES, format_type="detailed")
        assert "engineering/python" in result
