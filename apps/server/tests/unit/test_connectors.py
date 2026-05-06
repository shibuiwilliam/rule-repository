"""Unit tests for Source Connectors (Tier 2.6)."""

from __future__ import annotations

import pytest

from rulerepo_server.services.discovery.connectors.base import SourceConnector
from rulerepo_server.services.discovery.connectors.confluence import ConfluenceConnector
from rulerepo_server.services.discovery.connectors.notion import NotionConnector

# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Test that both connectors implement the SourceConnector Protocol."""

    def test_confluence_is_source_connector(self) -> None:
        connector = ConfluenceConnector()
        assert isinstance(connector, SourceConnector)

    def test_notion_is_source_connector(self) -> None:
        connector = NotionConnector()
        assert isinstance(connector, SourceConnector)

    def test_confluence_has_name(self) -> None:
        connector = ConfluenceConnector()
        assert connector.name == "confluence"

    def test_notion_has_name(self) -> None:
        connector = NotionConnector()
        assert connector.name == "notion"


# ---------------------------------------------------------------------------
# Unconfigured connectors raise NotImplementedError
# ---------------------------------------------------------------------------


class TestUnconfiguredConnectorsRaise:
    """Test that unconfigured connectors raise NotImplementedError."""

    async def test_confluence_list_documents_raises(self) -> None:
        connector = ConfluenceConnector()
        with pytest.raises(NotImplementedError, match="Confluence connector not yet configured"):
            await connector.list_documents()

    async def test_confluence_fetch_document_raises(self) -> None:
        connector = ConfluenceConnector()
        with pytest.raises(NotImplementedError, match="Confluence connector not yet configured"):
            await connector.fetch_document("page-123")

    async def test_notion_list_documents_raises(self) -> None:
        connector = NotionConnector()
        with pytest.raises(NotImplementedError, match="Notion connector not yet configured"):
            await connector.list_documents()

    async def test_notion_fetch_document_raises(self) -> None:
        connector = NotionConnector()
        with pytest.raises(NotImplementedError, match="Notion connector not yet configured"):
            await connector.fetch_document("page-abc")


# ---------------------------------------------------------------------------
# Constructor accepts credentials
# ---------------------------------------------------------------------------


class TestConstructorAcceptsCredentials:
    """Test that connectors accept credential parameters."""

    def test_confluence_accepts_credentials(self) -> None:
        token = "secret-token"
        connector = ConfluenceConnector(
            base_url="https://example.atlassian.net",
            username="user@example.com",
            api_token=token,
        )
        assert connector.name == "confluence"

    def test_notion_accepts_api_key(self) -> None:
        connector = NotionConnector(api_key="secret-notion-key")
        assert connector.name == "notion"
