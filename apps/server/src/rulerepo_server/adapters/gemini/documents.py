"""Gemini document processing — Files API upload and inline parsing."""

from __future__ import annotations

from google import genai
from google.genai import types

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Pages threshold: use Files API for documents larger than this
FILES_API_PAGE_THRESHOLD = 3


async def upload_to_files_api(
    client: genai.Client,
    file_bytes: bytes,
    mime_type: str,
    display_name: str = "document",
) -> types.File:
    """Upload a document to the Gemini Files API for processing.

    Use for PDFs > a few pages. Files API is free, files persist 48 hours,
    max 50 MB / 1000 pages.

    Args:
        client: The google-genai Client instance.
        file_bytes: Raw file bytes.
        mime_type: MIME type of the file.
        display_name: Human-readable file name.

    Returns:
        The uploaded File object with URI for use in generation calls.
    """
    import io

    file_obj = io.BytesIO(file_bytes)
    file_obj.name = display_name

    uploaded = client.files.upload(
        file=file_obj,
        config=types.UploadFileConfig(
            mime_type=mime_type,
            display_name=display_name,
        ),
    )
    logger.info(
        "file_uploaded_to_gemini",
        file_name=uploaded.name,
        mime_type=mime_type,
        size=len(file_bytes),
    )
    return uploaded


def create_inline_part(file_bytes: bytes, mime_type: str) -> types.Part:
    """Create an inline Part for small documents.

    Args:
        file_bytes: Raw file bytes.
        mime_type: MIME type of the file.

    Returns:
        A Part that can be included directly in a generation request.
    """
    return types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
