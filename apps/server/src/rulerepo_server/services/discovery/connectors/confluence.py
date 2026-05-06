"""Confluence source connector.

Connects to Atlassian Confluence Cloud/Server to discover documents
containing rules, policies, and standards.

Required credentials (via environment variables):
    - ``CONFLUENCE_URL``: Base URL of the Confluence instance.
    - ``CONFLUENCE_USERNAME``: API user email.
    - ``CONFLUENCE_API_TOKEN``: API token for authentication.

Tier 2.6 — Source Connectors.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class ConfluenceConnector:
    """Connector for Atlassian Confluence document sources.

    Fetches pages from Confluence spaces for rule discovery. Supports
    filtering by space key, label, and content type.

    This is a stub implementation. Full integration requires the
    ``atlassian-python-api`` package and valid API credentials.
    """

    name: str = "confluence"

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self._base_url = base_url
        self._username = username
        self._api_token = api_token

    async def list_documents(self, **filters: Any) -> list[dict[str, Any]]:
        """List documents from Confluence.

        Args:
            **filters: Optional filters such as ``space_key``, ``label``,
                ``content_type``.

        Raises:
            NotImplementedError: Confluence connector not yet configured.
        """
        raise NotImplementedError(
            "Confluence connector not yet configured. "
            "Set CONFLUENCE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_API_TOKEN "
            "environment variables and install atlassian-python-api."
        )

    async def fetch_document(self, document_id: str) -> dict[str, Any]:
        """Fetch a single Confluence page by ID.

        Args:
            document_id: The Confluence page ID.

        Raises:
            NotImplementedError: Confluence connector not yet configured.
        """
        raise NotImplementedError(
            "Confluence connector not yet configured. "
            "Set CONFLUENCE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_API_TOKEN "
            "environment variables and install atlassian-python-api."
        )
