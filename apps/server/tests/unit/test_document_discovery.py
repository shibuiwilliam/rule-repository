"""Tests for Phase 8 document discovery components.

Covers DocumentSource/IncrementalSource protocols, contract corpus analyzer,
and connector protocols.
"""

from __future__ import annotations

import pytest

from rulerepo_server.services.discovery.analyzers.base import DiscoveryContext
from rulerepo_server.services.discovery.analyzers.contract_corpus import (
    ContractCorpusAnalyzer,
    _find_representative,
    _select_contract_files,
)
from rulerepo_server.services.discovery.connectors.base import (
    ChangeEvent,
    DocumentMeta,
    SourceQuery,
)
from rulerepo_server.services.discovery.sources.contract_docx import (
    extract_from_docx,
)

# ---------------------------------------------------------------------------
# Protocol types
# ---------------------------------------------------------------------------


class TestSourceQuery:
    def test_defaults(self) -> None:
        q = SourceQuery()
        assert q.folder_id == ""
        assert q.max_results == 100
        assert q.modified_after is None

    def test_with_params(self) -> None:
        q = SourceQuery(
            folder_id="folder-123",
            query="policy",
            mime_types=["application/pdf"],
            max_results=50,
        )
        assert q.folder_id == "folder-123"
        assert q.mime_types == ["application/pdf"]


class TestDocumentMeta:
    def test_basic(self) -> None:
        meta = DocumentMeta(
            id="doc-1",
            title="HR Policy",
            mime_type="application/pdf",
            source="sharepoint",
        )
        assert meta.id == "doc-1"
        assert meta.source == "sharepoint"


class TestChangeEvent:
    def test_basic(self) -> None:
        event = ChangeEvent(
            document_id="doc-1",
            change_type="updated",
            cursor="cursor-abc",
        )
        assert event.change_type == "updated"
        assert event.cursor == "cursor-abc"


# ---------------------------------------------------------------------------
# Contract corpus analyzer
# ---------------------------------------------------------------------------


class TestContractCorpusAnalyzer:
    """Tests for ContractCorpusAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_insufficient_contracts(self) -> None:
        """With fewer than 3 contracts, returns empty."""
        context = DiscoveryContext(
            file_paths=["contract1.txt"],
            file_contents={
                "contract1.txt": "Article 1. Definitions\nSome text.\n",
            },
        )
        analyzer = ContractCorpusAnalyzer()
        patterns = await analyzer.analyze(context)
        assert patterns == []

    @pytest.mark.asyncio
    async def test_analyze_corpus(self) -> None:
        """With 3+ contracts sharing clause types, should find patterns."""
        nda_template = (
            "Article 1. Confidentiality\n"
            "All confidential information shall be protected and not disclosed.\n\n"
            "Article 2. Term\n"
            "This agreement is valid for two years from the effective date.\n\n"
            "Article 3. Governing Law\n"
            "This agreement shall be governed by the laws of Japan.\n"
        )
        context = DiscoveryContext(
            file_paths=[
                "contracts/nda_acme.txt",
                "contracts/nda_globex.txt",
                "contracts/nda_initech.txt",
            ],
            file_contents={
                "contracts/nda_acme.txt": nda_template.replace("Acme", "acme"),
                "contracts/nda_globex.txt": nda_template.replace("Globex", "globex"),
                "contracts/nda_initech.txt": nda_template.replace("Initech", "initech"),
            },
        )
        analyzer = ContractCorpusAnalyzer()
        patterns = await analyzer.analyze(context)

        # Should find standard patterns for common clause types
        assert len(patterns) > 0
        # At least confidentiality should be detected (present in all 3)
        clause_types_found = [p.scope for p in patterns]
        assert any("confidentiality" in s for s in clause_types_found)

    @pytest.mark.asyncio
    async def test_analyze_ignores_non_contract_files(self) -> None:
        """Non-contract files should be ignored."""
        context = DiscoveryContext(
            file_paths=["readme.md", "config.yaml", "app.py"],
            file_contents={
                "readme.md": "# Project README\nThis is a project.",
                "config.yaml": "key: value",
                "app.py": "def main(): pass",
            },
        )
        analyzer = ContractCorpusAnalyzer()
        patterns = await analyzer.analyze(context)
        assert patterns == []


class TestSelectContractFiles:
    def test_selects_by_filename(self) -> None:
        context = DiscoveryContext(
            file_paths=["nda.txt", "readme.md"],
            file_contents={
                "nda.txt": "Article 1. Terms\n...",
                "readme.md": "# README",
            },
        )
        result = _select_contract_files(context)
        assert len(result) == 1

    def test_selects_by_content(self) -> None:
        context = DiscoveryContext(
            file_paths=["doc.txt"],
            file_contents={
                "doc.txt": "This Agreement is entered into by and between the Parties hereto. " * 20,
            },
        )
        result = _select_contract_files(context)
        assert len(result) == 1


class TestFindRepresentative:
    def test_single_text(self) -> None:
        assert _find_representative(["hello"]) == "hello"

    def test_empty(self) -> None:
        assert _find_representative([]) == ""

    def test_picks_most_similar(self) -> None:
        texts = [
            "The receiving party shall protect confidential information.",
            "The receiving party must protect confidential information.",
            "Something completely different about payment terms.",
        ]
        rep = _find_representative(texts)
        # Should pick one of the first two (more similar to each other)
        assert "confidential" in rep.lower()


# ---------------------------------------------------------------------------
# Contract DOCX extraction
# ---------------------------------------------------------------------------


class TestContractDocxExtraction:
    @pytest.mark.asyncio
    async def test_extract_empty_bytes(self) -> None:
        """Empty DOCX bytes should return empty list."""
        result = await extract_from_docx(b"")
        assert result == []
