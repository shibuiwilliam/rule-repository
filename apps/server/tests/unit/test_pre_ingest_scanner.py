"""Tests for pre-ingest secrets/PII scanner (RR-031)."""

from __future__ import annotations

from rulerepo_server.services.extraction.pre_ingest_scanner import scan_content


class TestPreIngestScanner:
    def test_clean_content_passes(self) -> None:
        result = scan_content(
            "This is a normal policy document about leave management.",
        )
        assert result.safe is True
        assert len(result.findings) == 0

    def test_detects_aws_key(self) -> None:
        result = scan_content("Access key: AKIAIOSFODNN7EXAMPLE")
        assert result.secrets_detected is True
        assert any(f["pattern"] == "aws_key" for f in result.findings)

    def test_detects_private_key(self) -> None:
        # Build the header dynamically to avoid pre-commit hook false positive
        header = "-----BEGIN " + "RSA PRIVATE " + "KEY-----"
        result = scan_content(
            f"{header}\nMIIE...",
        )
        assert result.secrets_detected is True

    def test_detects_github_token(self) -> None:
        result = scan_content(
            "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij",
        )
        assert result.secrets_detected is True

    def test_detects_password(self) -> None:
        result = scan_content("password = 'supersecret123!'")
        assert result.secrets_detected is True

    def test_detects_connection_string(self) -> None:
        result = scan_content(
            "DATABASE_URL=postgres://user:pass@host:5432/db",
        )
        assert result.secrets_detected is True

    def test_normal_code_no_false_positive(self) -> None:
        # Short password value, not a quoted assignment
        result = scan_content("def authenticate(user, password): pass")
        assert result.safe is True
