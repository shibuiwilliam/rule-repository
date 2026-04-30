"""Unit tests for PII sanitization module."""

from rulerepo_server.core.pii import contains_pii, sanitize_dict, sanitize_text


class TestSanitizeText:
    def test_email_redacted(self) -> None:
        assert "[EMAIL_REDACTED]" in sanitize_text("Contact john@example.com for details")

    def test_phone_redacted(self) -> None:
        assert "[PHONE_REDACTED]" in sanitize_text("Call 555-123-4567 now")

    def test_ssn_redacted(self) -> None:
        assert "[SSN_REDACTED]" in sanitize_text("SSN: 123-45-6789")

    def test_credit_card_redacted(self) -> None:
        assert "[CARD_REDACTED]" in sanitize_text("Card: 4111 1111 1111 1111")

    def test_no_pii_unchanged(self) -> None:
        text = "All deployments must go through staging"
        assert sanitize_text(text) == text

    def test_multiple_pii_types(self) -> None:
        text = "Email john@example.com or call 555-123-4567"
        result = sanitize_text(text)
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "john@example.com" not in result


class TestSanitizeDict:
    def test_sanitizes_string_values(self) -> None:
        data = {"name": "John", "email": "john@example.com", "count": 5}
        result = sanitize_dict(data)
        assert result["email"] == "[EMAIL_REDACTED]"
        assert result["count"] == 5

    def test_nested_dict(self) -> None:
        data = {"contact": {"email": "john@example.com"}}
        result = sanitize_dict(data)
        assert result["contact"]["email"] == "[EMAIL_REDACTED]"  # type: ignore[index]

    def test_list_values(self) -> None:
        data = {"emails": ["a@example.com", "b@example.com"]}
        result = sanitize_dict(data)
        assert all(item == "[EMAIL_REDACTED]" for item in result["emails"])  # type: ignore[union-attr]


class TestContainsPii:
    def test_detects_email(self) -> None:
        assert contains_pii("Contact john@example.com")

    def test_no_pii(self) -> None:
        assert not contains_pii("All code must be reviewed")
