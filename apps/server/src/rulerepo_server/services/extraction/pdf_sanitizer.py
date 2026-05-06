"""PDF sanitizer — strips dangerous content before LLM processing.

Re-encodes PDFs to remove JavaScript, embedded files, XFA forms, and
active content. Must be run on all uploaded PDFs before passing to the
Gemini Files API.

Uses pikepdf for safe PDF manipulation. Falls back to a basic size
check if pikepdf is not available.

See: CLAUDE.md §9.4, IMPROVEMENT.md §5.3.
"""

from __future__ import annotations

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

try:
    import pikepdf

    _PIKEPDF_AVAILABLE = True
except ImportError:
    _PIKEPDF_AVAILABLE = False


class PDFSanitizationError(Exception):
    """Raised when a PDF cannot be safely sanitized."""


def sanitize_pdf(content: bytes) -> bytes:
    """Sanitize a PDF by stripping dangerous content.

    Removes JavaScript, embedded files, XFA forms, and active content.
    Re-encodes the PDF to ensure a clean output.

    Args:
        content: Raw PDF bytes.

    Returns:
        Sanitized PDF bytes.

    Raises:
        PDFSanitizationError: If the PDF exceeds size limits or cannot
            be processed.
    """
    if len(content) > MAX_PDF_SIZE_BYTES:
        msg = f"PDF exceeds maximum size ({len(content)} bytes > {MAX_PDF_SIZE_BYTES} bytes)"
        raise PDFSanitizationError(msg)

    if not _PIKEPDF_AVAILABLE:
        logger.warning("pikepdf_not_available", msg="PDF sanitization limited to size check only")
        return content

    import io

    try:
        pdf = pikepdf.Pdf.open(io.BytesIO(content))
    except Exception as exc:
        msg = f"Failed to parse PDF: {exc}"
        raise PDFSanitizationError(msg) from exc

    # Strip JavaScript actions
    if "/Names" in pdf.Root and "/JavaScript" in pdf.Root["/Names"]:
        del pdf.Root["/Names"]["/JavaScript"]
        logger.info("pdf_sanitizer_stripped_javascript")

    # Strip embedded files
    if "/Names" in pdf.Root and "/EmbeddedFiles" in pdf.Root["/Names"]:
        del pdf.Root["/Names"]["/EmbeddedFiles"]
        logger.info("pdf_sanitizer_stripped_embedded_files")

    # Strip XFA forms (used in dynamic PDF forms, potential attack vector)
    if "/AcroForm" in pdf.Root:
        acroform = pdf.Root["/AcroForm"]
        if "/XFA" in acroform:
            del acroform["/XFA"]
            logger.info("pdf_sanitizer_stripped_xfa")

    # Strip OpenAction (auto-execute on open)
    if "/OpenAction" in pdf.Root:
        del pdf.Root["/OpenAction"]
        logger.info("pdf_sanitizer_stripped_open_action")

    # Re-encode to clean output
    output = io.BytesIO()
    pdf.save(output)
    pdf.close()

    sanitized = output.getvalue()
    logger.info(
        "pdf_sanitized",
        original_size=len(content),
        sanitized_size=len(sanitized),
    )
    return sanitized
