"""Base protocols for source connectors.

All external document source integrations must conform to one of these protocols.
``SourceConnector`` is the base; ``DocumentSource`` adds structured document
retrieval; ``IncrementalSource`` adds change-tracking for continuous ingestion.

See: CLAUDE.md §16.1, PROJECT.md §6.4
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
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


@dataclass(frozen=True)
class SourceQuery:
    """Query parameters for document source listing.

    Attributes:
        folder_id: Folder or space identifier to scope the search.
        query: Text query for filtering documents.
        mime_types: Acceptable MIME types.
        modified_after: Only return documents modified after this date.
        max_results: Maximum number of results to return.
    """

    folder_id: str = ""
    query: str = ""
    mime_types: list[str] = field(default_factory=list)
    modified_after: datetime | None = None
    max_results: int = 100


@dataclass(frozen=True)
class DocumentMeta:
    """Metadata for a document from an external source.

    Attributes:
        id: Source-specific document identifier.
        title: Document title.
        mime_type: MIME type of the document content.
        source: Source connector name (e.g., "sharepoint", "google_drive").
        modified_at: Last modification timestamp.
        url: Direct link to the document in the source system.
        metadata: Additional source-specific metadata.
    """

    id: str
    title: str
    mime_type: str = ""
    source: str = ""
    modified_at: datetime | None = None
    url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChangeEvent:
    """A change event from an incremental source.

    Attributes:
        document_id: The changed document's identifier.
        change_type: Type of change ("created", "updated", "deleted").
        changed_at: When the change occurred.
        cursor: Opaque cursor for resuming change tracking.
        metadata: Additional change-specific metadata.
    """

    document_id: str
    change_type: str  # "created" | "updated" | "deleted"
    changed_at: datetime | None = None
    cursor: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DocumentSource(Protocol):
    """Protocol for structured document sources.

    Extends SourceConnector with typed query, content retrieval,
    and metadata access. Used by discovery analyzers.

    See: CLAUDE.md §16.1
    """

    name: str

    async def list_documents(self, query: SourceQuery) -> AsyncIterator[DocumentMeta]:
        """List documents matching the query.

        Args:
            query: Structured query parameters.

        Yields:
            DocumentMeta objects for matching documents.
        """
        ...

    async def get_content(self, doc_id: str) -> bytes:
        """Retrieve raw content of a document.

        Args:
            doc_id: Source-specific document identifier.

        Returns:
            Raw document bytes.
        """
        ...

    async def get_metadata(self, doc_id: str) -> dict[str, Any]:
        """Retrieve metadata for a document.

        Args:
            doc_id: Source-specific document identifier.

        Returns:
            Metadata dict with source-specific fields.
        """
        ...


@runtime_checkable
class IncrementalSource(DocumentSource, Protocol):
    """Protocol for sources that support change tracking.

    Enables continuous ingestion: when a regulation is amended or a
    policy document is updated, the system picks it up automatically.

    See: CLAUDE.md §16.1
    """

    async def changes_since(self, cursor: str) -> AsyncIterator[ChangeEvent]:
        """Yield change events since the given cursor.

        Args:
            cursor: Opaque cursor from a previous ``ChangeEvent``.
                Empty string means "from the beginning."

        Yields:
            ChangeEvent objects for each detected change.
        """
        ...
