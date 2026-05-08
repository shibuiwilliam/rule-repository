"""SharePoint site connector for document discovery.

Fetches documents from SharePoint Online sites for rule extraction.
Requires Microsoft Graph API credentials.

See: CLAUDE.md §16.2
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.connectors.base import (
    ChangeEvent,
    DocumentMeta,
    SourceQuery,
)

logger = get_logger(__name__)


class SharePointConnector:
    """Connects to SharePoint Online via Microsoft Graph API.

    Implements IncrementalSource for continuous ingestion of policy documents.

    Configuration:
        SHAREPOINT_TENANT: Azure AD tenant ID
        SHAREPOINT_CLIENT_ID: App registration client ID
        SHAREPOINT_CLIENT_SECRET: App registration client secret
        SHAREPOINT_SITE_ID: Target SharePoint site ID
    """

    name = "sharepoint"

    def __init__(
        self,
        *,
        tenant_id: str = "",
        client_id: str = "",
        client_secret: str = "",
        site_id: str = "",
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._site_id = site_id

    async def list_documents(self, query: SourceQuery | None = None, **filters: Any) -> AsyncIterator[DocumentMeta]:
        """List documents from a SharePoint site or document library.

        Args:
            query: Structured query parameters.
            **filters: Legacy filter parameters.

        Yields:
            DocumentMeta objects for matching documents.
        """
        logger.info(
            "sharepoint_list_documents",
            site_id=self._site_id,
            query=query,
        )
        # Stub: production implementation would use Microsoft Graph API
        # GET /sites/{site-id}/drive/root/children
        # or GET /sites/{site-id}/drives/{drive-id}/root/search(q='{query}')
        return
        yield  # make this an async generator  # type: ignore[misc]

    async def get_content(self, doc_id: str) -> bytes:
        """Download document content from SharePoint.

        Args:
            doc_id: SharePoint drive item ID.

        Returns:
            Raw document bytes.
        """
        logger.info("sharepoint_get_content", doc_id=doc_id)
        # Stub: GET /sites/{site-id}/drive/items/{item-id}/content
        return b""

    async def get_metadata(self, doc_id: str) -> dict[str, Any]:
        """Get document metadata from SharePoint.

        Args:
            doc_id: SharePoint drive item ID.

        Returns:
            Document metadata including name, size, modified date.
        """
        logger.info("sharepoint_get_metadata", doc_id=doc_id)
        # Stub: GET /sites/{site-id}/drive/items/{item-id}
        return {"id": doc_id, "source": self.name}

    async def changes_since(self, cursor: str) -> AsyncIterator[ChangeEvent]:
        """Track changes using SharePoint delta query.

        Args:
            cursor: Delta link token from previous sync.

        Yields:
            ChangeEvent for each document change.
        """
        logger.info("sharepoint_changes_since", cursor=cursor[:20] if cursor else "start")
        # Stub: GET /sites/{site-id}/drive/root/delta
        # Uses @odata.deltaLink for incremental sync
        return
        yield  # make this an async generator  # type: ignore[misc]

    async def fetch_document(self, document_id: str) -> dict[str, Any]:
        """Legacy SourceConnector interface."""
        meta = await self.get_metadata(document_id)
        content = await self.get_content(document_id)
        return {**meta, "content": content.decode("utf-8", errors="replace")}
