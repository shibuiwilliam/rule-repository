"""Local file storage adapter for uploaded documents."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class LocalFileStorage:
    """Stores uploaded files on the local filesystem.

    For production, this would be swapped with an S3-compatible implementation.
    """

    def __init__(self, base_path: str | None = None) -> None:
        self._base_path = Path(base_path or get_settings().file_storage_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    async def store(self, file_bytes: bytes, filename: str, mime_type: str) -> str:
        """Store a file and return its document ID.

        Args:
            file_bytes: Raw file content.
            filename: Original filename.
            mime_type: MIME type of the file.

        Returns:
            A unique document ID for retrieval.
        """
        doc_id = str(uuid4())
        ext = Path(filename).suffix
        storage_name = f"{doc_id}{ext}"
        path = self._base_path / storage_name

        async with aiofiles.open(path, "wb") as f:
            await f.write(file_bytes)

        logger.info(
            "file_stored",
            document_id=doc_id,
            filename=filename,
            mime_type=mime_type,
            size=len(file_bytes),
        )
        return doc_id

    async def retrieve(self, document_id: str) -> tuple[bytes, str]:
        """Retrieve a stored file by its document ID.

        Args:
            document_id: The document ID returned by store().

        Returns:
            Tuple of (file_bytes, storage_path).

        Raises:
            NotFoundError: If the file does not exist.
        """
        matches = list(self._base_path.glob(f"{document_id}*"))
        if not matches:
            raise NotFoundError("Document file", document_id)

        path = matches[0]
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()

        return content, str(path)

    def get_storage_path(self, document_id: str) -> str:
        """Get the filesystem path for a document.

        Args:
            document_id: The document ID.

        Returns:
            The full filesystem path string.
        """
        matches = list(self._base_path.glob(f"{document_id}*"))
        if not matches:
            return str(self._base_path / document_id)
        return str(matches[0])
