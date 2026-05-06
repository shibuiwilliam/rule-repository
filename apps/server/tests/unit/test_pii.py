"""Unit tests for PII sanitization and tokenizer modules."""

from rulerepo_server.core.pii import contains_pii, sanitize_dict, sanitize_text
from rulerepo_server.core.pii.tokenizer import PiiTokenizer

# ---------------------------------------------------------------------------
# Existing sanitize_text / sanitize_dict / contains_pii tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# PiiTokenizer tests (Tier 1.6)
# ---------------------------------------------------------------------------


class TestPiiTokenizerTokenize:
    """Tests for PiiTokenizer.tokenize()."""

    def setup_method(self) -> None:
        self.tokenizer = PiiTokenizer()

    def test_email_replaced_with_placeholder(self) -> None:
        text = "Contact john@example.com for details"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[EMAIL_1]" in result
        assert "john@example.com" not in result
        assert mapping["[EMAIL_1]"] == "john@example.com"

    def test_multiple_emails_get_unique_placeholders(self) -> None:
        text = "Email john@acme.com or jane@acme.com"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[EMAIL_1]" in result
        assert "[EMAIL_2]" in result
        assert mapping["[EMAIL_1]"] == "john@acme.com"
        assert mapping["[EMAIL_2]"] == "jane@acme.com"

    def test_phone_us_format(self) -> None:
        text = "Call 555-123-4567 now"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[PHONE_1]" in result
        assert "555-123-4567" not in result
        assert mapping["[PHONE_1]"] == "555-123-4567"

    def test_phone_international_format(self) -> None:
        text = "Call +1-555-123-4567 now"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[PHONE_1]" in result
        assert "+1-555-123-4567" not in result

    def test_phone_jp_format(self) -> None:
        text = "TEL: 03-1234-5678"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[PHONE_" in result
        assert "03-1234-5678" not in result

    def test_credit_card_replaced(self) -> None:
        text = "Card: 4111 1111 1111 1111"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[ID_1]" in result
        assert "4111 1111 1111 1111" not in result
        assert mapping["[ID_1]"] == "4111 1111 1111 1111"

    def test_ip_address_replaced(self) -> None:
        text = "Server at 192.168.1.100"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[IP_1]" in result
        assert "192.168.1.100" not in result
        assert mapping["[IP_1]"] == "192.168.1.100"

    def test_japanese_katakana_name(self) -> None:
        text = "担当者: タナカ タロウ です"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[PERSON_1]" in result
        assert "タナカ タロウ" not in result

    def test_japanese_kanji_name(self) -> None:
        text = "担当者は 田中 太郎 です"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[PERSON_1]" in result
        assert "田中 太郎" not in result

    def test_no_pii_returns_unchanged(self) -> None:
        text = "All deployments must go through staging"
        result, mapping = self.tokenizer.tokenize(text)
        assert result == text
        assert mapping == {}

    def test_multiple_pii_types_get_separate_counters(self) -> None:
        text = "Email john@acme.com from 192.168.1.1 or call 555-123-4567"
        result, mapping = self.tokenizer.tokenize(text)
        assert "[EMAIL_1]" in result
        assert "[IP_1]" in result
        assert "[PHONE_1]" in result
        assert len(mapping) == 3

    def test_empty_string(self) -> None:
        result, mapping = self.tokenizer.tokenize("")
        assert result == ""
        assert mapping == {}


class TestPiiTokenizerDetokenize:
    """Tests for PiiTokenizer.detokenize()."""

    def setup_method(self) -> None:
        self.tokenizer = PiiTokenizer()

    def test_detokenize_restores_email(self) -> None:
        mapping = {"[EMAIL_1]": "john@example.com"}
        result = self.tokenizer.detokenize("Contact [EMAIL_1] for details", mapping)
        assert result == "Contact john@example.com for details"

    def test_detokenize_restores_multiple(self) -> None:
        mapping = {
            "[EMAIL_1]": "john@acme.com",
            "[PHONE_1]": "555-123-4567",
        }
        text = "Email [EMAIL_1] or call [PHONE_1]"
        result = self.tokenizer.detokenize(text, mapping)
        assert result == "Email john@acme.com or call 555-123-4567"

    def test_detokenize_empty_mapping(self) -> None:
        text = "No PII here"
        result = self.tokenizer.detokenize(text, {})
        assert result == text

    def test_detokenize_placeholder_not_in_text(self) -> None:
        mapping = {"[EMAIL_1]": "john@example.com"}
        text = "No placeholders"
        result = self.tokenizer.detokenize(text, mapping)
        assert result == text


class TestPiiTokenizerRoundtrip:
    """Roundtrip tests: tokenize then detokenize should restore original text."""

    def setup_method(self) -> None:
        self.tokenizer = PiiTokenizer()

    def test_roundtrip_single_email(self) -> None:
        original = "Contact john@example.com for details"
        tokenized, mapping = self.tokenizer.tokenize(original)
        restored = self.tokenizer.detokenize(tokenized, mapping)
        assert restored == original

    def test_roundtrip_multiple_pii(self) -> None:
        original = "Email john@acme.com, call 555-123-4567, server 10.0.0.1"
        tokenized, mapping = self.tokenizer.tokenize(original)
        assert "john@acme.com" not in tokenized
        assert "555-123-4567" not in tokenized
        assert "10.0.0.1" not in tokenized
        restored = self.tokenizer.detokenize(tokenized, mapping)
        assert restored == original

    def test_roundtrip_japanese_name(self) -> None:
        original = "担当者: タナカ タロウ のメール john@example.com"
        tokenized, mapping = self.tokenizer.tokenize(original)
        restored = self.tokenizer.detokenize(tokenized, mapping)
        assert restored == original

    def test_roundtrip_credit_card(self) -> None:
        original = "Payment card: 4111 1111 1111 1111 confirmed"
        tokenized, mapping = self.tokenizer.tokenize(original)
        restored = self.tokenizer.detokenize(tokenized, mapping)
        assert restored == original

    def test_roundtrip_no_pii(self) -> None:
        original = "All code must be reviewed before merge"
        tokenized, mapping = self.tokenizer.tokenize(original)
        restored = self.tokenizer.detokenize(tokenized, mapping)
        assert restored == original
        assert mapping == {}

    def test_roundtrip_ip_addresses(self) -> None:
        original = "Servers: 192.168.1.1 and 10.0.0.1"
        tokenized, mapping = self.tokenizer.tokenize(original)
        restored = self.tokenizer.detokenize(tokenized, mapping)
        assert restored == original

    def test_each_call_independent(self) -> None:
        """Verify statelessness: counters reset between calls."""
        text1 = "Email a@example.com"
        text2 = "Email b@example.com"
        _, mapping1 = self.tokenizer.tokenize(text1)
        _, mapping2 = self.tokenizer.tokenize(text2)
        # Both should use [EMAIL_1] since calls are independent
        assert "[EMAIL_1]" in mapping1
        assert "[EMAIL_1]" in mapping2
        assert mapping1["[EMAIL_1]"] == "a@example.com"
        assert mapping2["[EMAIL_1]"] == "b@example.com"
