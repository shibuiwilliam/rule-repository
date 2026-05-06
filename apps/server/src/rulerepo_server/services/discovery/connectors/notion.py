"""Notion source connector.

Connects to the Notion API to discover pages and databases containing
rules, policies, and standards.

Required credentials (via environment variables):
    - ``NOTION_API_KEY``: Notion integration token (internal integration).

Tier 2.6 — Source Connectors.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class NotionConnector:
    """Connector for Notion document sources.

    Fetches pages and database entries from Notion workspaces for rule
    discovery.

    This is a stub implementation. Full integration requires the
    ``notion-client`` package and a valid integration token.
    """

    name: str = "notion"

    def __init__(
        self,
        api_key: str | None = None,
    ) -> None:
        self._api_key = api_key

    async def list_documents(self, **filters: Any) -> list[dict[str, Any]]:
        """List documents from Notion.

        Args:
            **filters: Optional filters such as ``database_id``,
                ``page_size``, ``start_cursor``.

        Raises:
            NotImplementedError: Notion connector not yet configured.
        """
        raise NotImplementedError(
            "Notion connector not yet configured. Set NOTION_API_KEY environment variable and install notion-client."
        )

    async def fetch_document(self, document_id: str) -> dict[str, Any]:
        """Fetch a single Notion page by ID.

        Args:
            document_id: The Notion page or block ID.

        Raises:
            NotImplementedError: Notion connector not yet configured.
        """
        raise NotImplementedError(
            "Notion connector not yet configured. Set NOTION_API_KEY environment variable and install notion-client."
        )
