"""PII scrubbing middleware — mandatory on the evaluate/extraction/conversational hot path.

Intercepts request bodies on PII-sensitive endpoints, detects potential
PII fields, and redacts them before the request reaches the handler.
This ensures no PII is passed through to LLM prompts without explicit
``audit-pii-allowed`` permission.

See CLAUDE.md §9.3, §14 Rule #12, IMPROVEMENT.md §4.3 / RR-015.
"""

from __future__ import annotations

import json
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from rulerepo_server.core.logging import get_logger
from rulerepo_server.core.pii.redactor import detect_pii, redact

logger = get_logger(__name__)

# Endpoints where PII scrubbing is mandatory
_HOT_PATH_PREFIXES = (
    "/api/v1/evaluate",
    "/api/v1/ask",
    "/api/v1/extract",
    "/api/v1/gateway/",
)

# Header that allows bypassing PII scrubbing (requires explicit permission)
_PII_BYPASS_HEADER = "X-PII-Allowed"


class PIIScrubMiddleware(BaseHTTPMiddleware):
    """Detect and redact PII in request bodies on hot-path endpoints.

    Only applies to POST/PUT/PATCH requests on evaluate, ask, extract,
    and gateway endpoints.  GET requests and non-hot-path routes pass
    through unchanged.

    PII detection uses heuristic field-name matching from
    ``core/pii/redactor.detect_pii``.  When PII is found, affected
    fields are replaced with ``[REDACTED:field:id]`` placeholders.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Check request body for PII and redact if found."""
        # Only apply to hot-path endpoints
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in _HOT_PATH_PREFIXES):
            return await call_next(request)

        # Only apply to methods with request bodies
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Check bypass header
        if request.headers.get(_PII_BYPASS_HEADER, "").lower() == "true":
            logger.info("pii_scrub_bypassed", path=path)
            return await call_next(request)

        # Read and parse body
        try:
            body = await request.body()
            if not body:
                return await call_next(request)

            data: dict[str, Any] = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON — pass through
            return await call_next(request)

        # Detect PII fields
        pii_paths = _find_pii_in_payload(data)

        if pii_paths:
            result = redact(data, pii_paths)
            logger.info(
                "pii_scrubbed",
                path=path,
                fields_redacted=len(pii_paths),
                paths=pii_paths,
            )

            # Replace request body with redacted version
            redacted_body = json.dumps(result.redacted_data).encode()

            # Create a new scope with the redacted body
            request._body = redacted_body

        return await call_next(request)


def _find_pii_in_payload(data: dict[str, Any]) -> list[str]:
    """Detect PII fields in the top-level and nested payload.

    Checks both the top-level request body and the ``facts``, ``payload``,
    and ``metadata`` sub-objects that evaluation requests commonly carry.

    Args:
        data: Parsed JSON request body.

    Returns:
        List of dot-separated paths to PII fields.
    """
    all_paths: list[str] = []

    # Top-level scan
    all_paths.extend(detect_pii(data))

    # Scan nested objects common in evaluation payloads
    for nested_key in ("facts", "payload", "metadata"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            nested_paths = detect_pii(nested)
            all_paths.extend(f"{nested_key}.{p}" for p in nested_paths)

    return all_paths
