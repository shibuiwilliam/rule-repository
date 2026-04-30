"""Documents resource — upload and extraction operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import ExtractionResult, UploadResult


class DocumentsResource:
    """Provides document upload and extraction via the REST API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def upload(self, file_path_or_bytes: str | bytes, filename: str | None = None) -> UploadResult:
        """Upload a document for rule extraction.

        Args:
            file_path_or_bytes: Path to a file or raw bytes.
            filename: Filename to use (required if passing bytes).

        Returns:
            UploadResult with document_id and metadata.
        """
        if isinstance(file_path_or_bytes, str):
            path = Path(file_path_or_bytes)
            filename = filename or path.name
            file_bytes = path.read_bytes()
        else:
            file_bytes = file_path_or_bytes
            filename = filename or "document"

        files = {"file": (filename, file_bytes)}
        resp = await self._client.post("/api/v1/documents/upload", files=files)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return UploadResult.model_validate(resp.json())

    async def extract(self, document_id: str) -> ExtractionResult:
        """Trigger rule extraction on an uploaded document.

        Args:
            document_id: The document's UUID string.

        Returns:
            ExtractionResult with candidate rules.
        """
        resp = await self._client.post(f"/api/v1/documents/{document_id}/extract")
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return ExtractionResult.model_validate(resp.json())

    async def get_extraction(self, extraction_id: str) -> ExtractionResult:
        """Get extraction results by ID.

        Args:
            extraction_id: The extraction's UUID string.

        Returns:
            ExtractionResult with candidate rules.
        """
        resp = await self._client.get(f"/api/v1/documents/extractions/{extraction_id}")
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return ExtractionResult.model_validate(resp.json())

    async def review(
        self,
        extraction_id: str,
        approved_indices: list[int] | None = None,
        edits: dict[int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Review extraction results — approve or edit candidates.

        Args:
            extraction_id: The extraction's UUID string.
            approved_indices: Indices of candidates to approve as-is.
            edits: Edited versions of candidates, keyed by index.

        Returns:
            Review result with created rule IDs.
        """
        body: dict[str, Any] = {"extraction_id": extraction_id}
        if approved_indices:
            body["approved_indices"] = approved_indices
        if edits:
            body["edits"] = edits
        resp = await self._client.post(
            f"/api/v1/documents/extractions/{extraction_id}/review",
            json=body,
        )
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return resp.json()
