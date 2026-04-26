"""Webhook outbound action — POST verdict to a callback URL.

Per CLAUDE_ENHANCE.md §3.4: response actions are fire-and-forget.
If a webhook callback fails, log the error and move on.
"""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def send_webhook(
    url: str,
    verdict: str,
    details: dict[str, Any],
    timeout: float = 10.0,
) -> bool:
    """POST a verdict to a callback URL.

    Args:
        url: The webhook URL to POST to.
        verdict: The evaluation verdict (ALLOW, DENY, NEEDS_CONFIRMATION).
        details: Additional evaluation details.
        timeout: Request timeout in seconds.

    Returns:
        True if the webhook was delivered successfully, False otherwise.
    """
    payload = {"verdict": verdict, **details}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            logger.info(
                "webhook_sent",
                url=url,
                status_code=resp.status_code,
                verdict=verdict,
            )
            return resp.is_success
    except Exception as exc:
        logger.warning("webhook_send_failed", url=url, error=str(exc))
        return False
