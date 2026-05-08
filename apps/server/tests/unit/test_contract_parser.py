"""Tests for the contract parser adapter.

Covers text parsing, clause extraction, and evaluation payload generation.
"""

from __future__ import annotations

from rulerepo_server.adapters.contract_parser import ContractParser, ParsedContract
from rulerepo_server.domain.contract import ContractScope, ContractType, PartyRole


class TestContractParser:
    """Tests for ContractParser.parse_text()."""

    def test_parse_simple_nda(self) -> None:
        text = (
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "Article 1. Definitions\n"
            "Confidential Information means any information disclosed by either party.\n\n"
            "Article 2. Obligations\n"
            "The Receiving Party shall maintain the confidentiality of all Confidential Information.\n\n"
            "Article 3. Term\n"
            "This Agreement shall remain in effect for two (2) years.\n"
        )
        scope = ContractScope(
            contract_type=ContractType.NDA,
            governing_law="japan",
            party_role=PartyRole.BOTH,
        )
        parser = ContractParser()
        result = parser.parse_text(text, title="Test NDA", scope=scope)

        assert isinstance(result, ParsedContract)
        assert result.clause_count == 3
        assert result.scope.contract_type == ContractType.NDA
        assert result.source_format == "text"
        assert result.document.title == "Test NDA"

    def test_parse_japanese_contract(self) -> None:
        text = (
            "秘密保持契約書\n\n"
            "第1条 定義\n秘密情報とは、開示者が受領者に開示する一切の情報をいう。\n\n"
            "第2条 秘密保持義務\n受領者は、秘密情報を厳に秘密として保持しなければならない。\n\n"
            "第3条 有効期間\n本契約の有効期間は2年間とする。\n"
        )
        parser = ContractParser()
        result = parser.parse_text(text)

        assert result.clause_count == 3
        assert result.document.clauses[0].id == "art1"

    def test_parse_empty_text(self) -> None:
        parser = ContractParser()
        result = parser.parse_text("")
        assert result.clause_count == 0

    def test_classified_clauses(self) -> None:
        text = (
            "Article 1. Confidentiality\n"
            "All confidential information shall be protected.\n\n"
            "Article 2. Payment\n"
            "Payment is due within 30 days.\n"
        )
        parser = ContractParser()
        result = parser.parse_text(text)

        assert len(result.classified_clauses) == 2
        # First clause should be classified as confidentiality
        assert result.classified_clauses[0].clause_type == "confidentiality"

    def test_references_resolved(self) -> None:
        text = (
            "Article 1. Definitions\nConfidential Information means...\n\n"
            "Article 2. Obligations\nAs defined in Article 1, the Receiving Party shall...\n"
        )
        parser = ContractParser()
        result = parser.parse_text(text)

        assert result.references is not None
        internal_refs = [r for r in result.references.references if r.reference_type == "internal"]
        assert any(r.target_clause_id == "art1" for r in internal_refs)


class TestParsedContractPayload:
    """Tests for ParsedContract.to_evaluation_payload()."""

    def test_payload_structure(self) -> None:
        text = (
            "Article 1. Confidentiality\nAll information is confidential.\n\n"
            "Article 2. Term\nThis agreement lasts two years.\n"
        )
        scope = ContractScope(
            contract_type=ContractType.NDA,
            governing_law="japan",
            counterparty_country="us",
            party_role=PartyRole.RECEIVING,
            language="en",
        )
        parser = ContractParser()
        result = parser.parse_text(text, scope=scope)
        payload = result.to_evaluation_payload()

        assert payload["contract_type"] == "nda"
        assert payload["governing_law"] == "japan"
        assert payload["counterparty_country"] == "us"
        assert payload["party_role"] == "receiving"
        assert payload["language"] == "en"
        assert payload["clause_count"] == 2
        assert len(payload["clauses"]) == 2
        assert payload["clauses"][0]["clause_id"] == "art1"
        assert "text" in payload["clauses"][0]

    def test_payload_with_empty_scope(self) -> None:
        parser = ContractParser()
        result = parser.parse_text("Article 1. Test\nSome text.\n")
        payload = result.to_evaluation_payload()

        assert payload["contract_type"] == "other"
        assert payload["governing_law"] == ""
        assert payload["clause_count"] == 1
