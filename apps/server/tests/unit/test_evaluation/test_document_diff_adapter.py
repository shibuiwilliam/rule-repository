"""Tests for the document_diff evaluation domain adapter."""

from __future__ import annotations

import pytest

from rulerepo_server.domain.contract import ContractScope, ContractType, PartyRole
from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.services.evaluation.adapters.base import EvaluationDomainAdapter
from rulerepo_server.services.evaluation.adapters.document_diff.adapter import (
    DocumentDiffAdapter,
)


class TestDocumentDiffAdapterProtocol:
    """Verify that DocumentDiffAdapter implements EvaluationDomainAdapter."""

    def test_implements_protocol(self) -> None:
        adapter = DocumentDiffAdapter()
        assert isinstance(adapter, EvaluationDomainAdapter)

    def test_domain_attribute(self) -> None:
        adapter = DocumentDiffAdapter()
        assert adapter.domain == "document_diff"


class TestDocumentDiffAdapterParse:
    """Test DocumentDiffAdapter.parse()."""

    @pytest.mark.asyncio
    async def test_parse_nda_diff(self) -> None:
        adapter = DocumentDiffAdapter()
        payload = {
            "contract_type": "nda",
            "governing_law": "japan",
            "counterparty_country": "us",
            "party_role": "disclosing",
            "language": "en",
            "old_text": "Original NDA text with standard clauses.",
            "new_text": "Revised NDA text with modified clauses.",
            "description": "Updated confidentiality period from 3 to 5 years",
            "actor": "legal-team",
        }
        ctx = await adapter.parse(payload)
        assert isinstance(ctx, EvaluationContext)
        assert ctx.facts["contract_type"] == "nda"
        assert ctx.facts["governing_law"] == "japan"
        assert ctx.facts["counterparty_country"] == "us"
        assert ctx.facts["party_role"] == "disclosing"
        assert ctx.facts["contract_language"] == "en"
        assert ctx.facts["old_text"] == "Original NDA text with standard clauses."
        assert ctx.facts["new_text"] == "Revised NDA text with modified clauses."
        assert ctx.actor == "legal-team"
        assert ctx.narrative == "Updated confidentiality period from 3 to 5 years"

    @pytest.mark.asyncio
    async def test_parse_with_explicit_diff(self) -> None:
        adapter = DocumentDiffAdapter()
        diff = "--- old\n+++ new\n@@ -1 +1 @@\n-3 years\n+5 years"
        payload = {
            "contract_type": "msa",
            "diff": diff,
        }
        ctx = await adapter.parse(payload)
        assert ctx.diff == diff

    @pytest.mark.asyncio
    async def test_parse_generates_diff_note(self) -> None:
        adapter = DocumentDiffAdapter()
        payload = {
            "contract_type": "sow",
            "old_text": "Short old text",
            "new_text": "Longer new text with additions",
        }
        ctx = await adapter.parse(payload)
        assert ctx.diff is not None
        assert "old" in ctx.diff
        assert "new" in ctx.diff

    @pytest.mark.asyncio
    async def test_parse_minimal_payload(self) -> None:
        adapter = DocumentDiffAdapter()
        ctx = await adapter.parse({})
        assert isinstance(ctx, EvaluationContext)

    @pytest.mark.asyncio
    async def test_parse_unknown_contract_type(self) -> None:
        adapter = DocumentDiffAdapter()
        payload = {"contract_type": "xyz_unknown"}
        ctx = await adapter.parse(payload)
        assert ctx.facts["contract_type"] == "other"


class TestDocumentDiffAdapterResolveScopes:
    """Test DocumentDiffAdapter.resolve_scopes()."""

    def test_resolve_nda(self) -> None:
        adapter = DocumentDiffAdapter()
        scopes = adapter.resolve_scopes({"contract_type": "nda"})
        assert "legal/nda" in scopes
        assert "legal/confidentiality" in scopes

    def test_resolve_msa(self) -> None:
        adapter = DocumentDiffAdapter()
        scopes = adapter.resolve_scopes({"contract_type": "msa"})
        assert "legal/msa" in scopes
        assert "legal/general" in scopes

    def test_resolve_with_governing_law(self) -> None:
        adapter = DocumentDiffAdapter()
        scopes = adapter.resolve_scopes(
            {
                "contract_type": "dpa",
                "governing_law": "EU-GDPR",
            }
        )
        assert "legal/dpa" in scopes
        assert "legal/jurisdiction/eu-gdpr" in scopes

    def test_resolve_unknown_type(self) -> None:
        adapter = DocumentDiffAdapter()
        scopes = adapter.resolve_scopes({"contract_type": "unknown_type"})
        assert "legal/general" in scopes

    def test_resolve_empty_payload(self) -> None:
        adapter = DocumentDiffAdapter()
        scopes = adapter.resolve_scopes({})
        assert "legal/general" in scopes


class TestDocumentDiffAdapterPromptFragments:
    """Test DocumentDiffAdapter.get_prompt_fragments()."""

    def test_returns_required_keys(self) -> None:
        adapter = DocumentDiffAdapter()
        fragments = adapter.get_prompt_fragments()
        assert "domain_intro" in fragments
        assert "context_format" in fragments
        assert isinstance(fragments["domain_intro"], str)
        assert isinstance(fragments["context_format"], str)
        assert len(fragments["domain_intro"]) > 0
        assert len(fragments["context_format"]) > 0


class TestContractScope:
    """Test ContractScope creation and enum values."""

    def test_create_full_scope(self) -> None:
        scope = ContractScope(
            contract_type=ContractType.NDA,
            governing_law="japan",
            counterparty_country="us",
            party_role=PartyRole.DISCLOSING,
            language="en",
        )
        assert scope.contract_type == ContractType.NDA
        assert scope.governing_law == "japan"
        assert scope.counterparty_country == "us"
        assert scope.party_role == PartyRole.DISCLOSING
        assert scope.language == "en"

    def test_create_minimal_scope(self) -> None:
        scope = ContractScope()
        assert scope.contract_type is None
        assert scope.governing_law is None

    def test_contract_type_values(self) -> None:
        assert ContractType.NDA == "nda"
        assert ContractType.MSA == "msa"
        assert ContractType.SOW == "sow"
        assert ContractType.DPA == "dpa"
        assert ContractType.LEASE == "lease"
        assert ContractType.SALES == "sales"
        assert ContractType.OTHER == "other"

    def test_party_role_values(self) -> None:
        assert PartyRole.DISCLOSING == "disclosing"
        assert PartyRole.RECEIVING == "receiving"
        assert PartyRole.BOTH == "both"

    def test_frozen(self) -> None:
        scope = ContractScope(contract_type=ContractType.NDA)
        with pytest.raises(AttributeError):
            scope.contract_type = ContractType.MSA  # type: ignore[misc]
