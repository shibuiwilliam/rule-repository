"""Base protocol for source connectors.

All external document source integrations must conform to this protocol.

Tier 2.6 — Source Connectors.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceConnector(Protocol):
    """Protocol for external document source connectors.

    Implementations fetch documents from external systems (Confluence,
    Notion, e-Gov, EUR-Lex, etc.) and normalize them for the discovery
    pipeline.
    """

    name: str

    async def list_documents(self, **filters: Any) -> list[dict[str, Any]]:
        """List available documents from the source, with optional filters.

        Args:
            **filters: Source-specific filter parameters (e.g., space key,
                database ID, date range).

        Returns:
            A list of document metadata dicts, each containing at least
            ``id`` and ``title`` keys.
        """
        ...

    async def fetch_document(self, document_id: str) -> dict[str, Any]:
        """Fetch a single document by its source-specific ID.

        Args:
            document_id: The document identifier in the external system.

        Returns:
            A dict containing at least ``id``, ``title``, ``content``,
            and ``source`` keys.
        """
        ...
