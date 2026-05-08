"""Google Drive connector for document discovery.

Fetches documents from Google Drive folders for rule extraction.
Requires Google Service Account or OAuth credentials.

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


class GoogleDriveConnector:
    """Connects to Google Drive via the Drive API v3.

    Implements IncrementalSource for continuous ingestion of policy documents.

    Configuration:
        GOOGLE_DRIVE_CREDENTIALS: Path to service account JSON or OAuth token
        GOOGLE_DRIVE_FOLDER_ID: Root folder ID to scan
    """

    name = "google_drive"

    def __init__(
        self,
        *,
        credentials_path: str = "",
        folder_id: str = "",
    ) -> None:
        self._credentials_path = credentials_path
        self._folder_id = folder_id

    async def list_documents(self, query: SourceQuery | None = None, **filters: Any) -> AsyncIterator[DocumentMeta]:
        """List documents from a Google Drive folder.

        Args:
            query: Structured query parameters.
            **filters: Legacy filter parameters.

        Yields:
            DocumentMeta objects for matching documents.
        """
        logger.info(
            "google_drive_list_documents",
            folder_id=self._folder_id,
            query=query,
        )
        # Stub: production implementation would use Google Drive API v3
        # files().list(q="'{folder_id}' in parents", ...)
        return
        yield  # make this an async generator  # type: ignore[misc]

    async def get_content(self, doc_id: str) -> bytes:
        """Download document content from Google Drive.

        For Google Docs/Sheets/Slides, exports as PDF.
        For uploaded files (PDF, DOCX), downloads the original.

        Args:
            doc_id: Google Drive file ID.

        Returns:
            Raw document bytes.
        """
        logger.info("google_drive_get_content", doc_id=doc_id)
        # Stub: files().get_media(fileId=doc_id) or
        #       files().export_media(fileId=doc_id, mimeType='application/pdf')
        return b""

    async def get_metadata(self, doc_id: str) -> dict[str, Any]:
        """Get file metadata from Google Drive.

        Args:
            doc_id: Google Drive file ID.

        Returns:
            File metadata including name, MIME type, modified date.
        """
        logger.info("google_drive_get_metadata", doc_id=doc_id)
        # Stub: files().get(fileId=doc_id, fields="*")
        return {"id": doc_id, "source": self.name}

    async def changes_since(self, cursor: str) -> AsyncIterator[ChangeEvent]:
        """Track changes using Google Drive changes API.

        Args:
            cursor: Page token from previous changes list.

        Yields:
            ChangeEvent for each document change.
        """
        logger.info("google_drive_changes_since", cursor=cursor[:20] if cursor else "start")
        # Stub: changes().list(pageToken=cursor, ...)
        # Uses startPageToken for initial sync
        return
        yield  # make this an async generator  # type: ignore[misc]

    async def fetch_document(self, document_id: str) -> dict[str, Any]:
        """Legacy SourceConnector interface."""
        meta = await self.get_metadata(document_id)
        content = await self.get_content(document_id)
        return {**meta, "content": content.decode("utf-8", errors="replace")}
