"""Tests for PII scrubbing middleware (RR-015).

Validates that PII fields are detected and redacted on hot-path
endpoints before reaching the handler.
"""

from __future__ import annotations

from rulerepo_server.core.pii_middleware import _find_pii_in_payload


class TestFindPIIInPayload:
    """Test PII detection in evaluation payloads."""

    def test_detects_top_level_email(self) -> None:
        data = {"email": "user@example.com", "diff": "some code"}
        paths = _find_pii_in_payload(data)
        assert any("email" in p for p in paths)

    def test_detects_nested_facts_email(self) -> None:
        data = {
            "diff": "code",
            "facts": {"email": "john@example.com", "department": "Engineering"},
        }
        paths = _find_pii_in_payload(data)
        assert any("email" in p for p in paths)

    def test_detects_ssn_in_payload(self) -> None:
        data = {
            "evaluable": {
                "artifact_type": "attendance_record",
                "payload": {"ssn": "123-45-6789", "hours": 8},
            }
        }
        paths = _find_pii_in_payload(data)
        assert any("ssn" in p for p in paths)

    def test_no_pii_in_clean_payload(self) -> None:
        data = {"diff": "- old\n+ new", "scope": "engineering/python"}
        paths = _find_pii_in_payload(data)
        assert len(paths) == 0

    def test_detects_phone_in_metadata(self) -> None:
        data = {
            "metadata": {"phone": "+1234567890"},
            "diff": "code",
        }
        paths = _find_pii_in_payload(data)
        assert any("phone" in p for p in paths)

    def test_detects_salary_in_facts(self) -> None:
        data = {
            "facts": {"salary": 50000, "title": "Engineer"},
        }
        paths = _find_pii_in_payload(data)
        assert any("salary" in p for p in paths)

    def test_detects_address_field(self) -> None:
        data = {"address": "123 Main St", "scope": "hr"}
        paths = _find_pii_in_payload(data)
        assert any("address" in p for p in paths)
