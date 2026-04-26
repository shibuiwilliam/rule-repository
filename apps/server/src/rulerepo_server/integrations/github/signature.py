"""GitHub webhook signature verification.

Per CLAUDE_ENHANCE.md §3.3: verify X-Hub-Signature-256 using GITHUB_WEBHOOK_SECRET.
Use hmac.compare_digest for constant-time comparison.
"""

from __future__ import annotations

import hashlib
import hmac

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


def verify_github_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verify a GitHub webhook signature.

    Args:
        payload: The raw request body bytes.
        signature_header: The X-Hub-Signature-256 header value.

    Returns:
        True if the signature is valid or verification is skipped.
    """
    settings = get_settings()

    # Dev mode: skip verification if configured
    if not settings.github_webhook_secret:
        logger.debug("github_signature_skip", reason="no_secret_configured")
        return True

    if not signature_header:
        logger.warning("github_signature_missing")
        return False

    expected = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )

    valid = hmac.compare_digest(expected, signature_header)
    if not valid:
        logger.warning("github_signature_invalid")
    return valid
