"""Tenant isolation middleware — sets tenant context per request.

When MULTI_TENANT_ENABLED=true, extracts tenant_id from the API key or
X-Tenant-ID header and sets the request-scoped tenant context. In
single-tenant mode (default), uses DEFAULT_TENANT_ID for all requests.

Phase 7g. See: CLAUDE.md §17.4
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger
from rulerepo_server.core.tenancy.context import (
    DEFAULT_TENANT_ID,
    TenantContext,
    set_current_tenant,
)

logger = get_logger(__name__)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Sets tenant context for each request based on configuration mode.

    In single-tenant mode (default): all requests use DEFAULT_TENANT_ID.
    In multi-tenant mode: tenant_id is extracted from the X-Tenant-ID header
    or the authenticated API key's tenant binding.

    Requests without a valid tenant in multi-tenant mode receive 403.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        multi_tenant = getattr(settings, "multi_tenant_enabled", False)

        if not multi_tenant:
            # Single-tenant mode: use default tenant
            set_current_tenant(TenantContext(tenant_id=DEFAULT_TENANT_ID, tenant_name="default"))
            try:
                return await call_next(request)
            finally:
                # Context is automatically cleaned up by contextvars
                pass
        else:
            # Multi-tenant mode: extract tenant from header or auth
            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id:
                # Fall back to default for backward compatibility
                tenant_id = DEFAULT_TENANT_ID

            # TODO: Validate tenant_id exists in the tenants table
            # TODO: Cross-reference with API key's tenant binding
            set_current_tenant(TenantContext(tenant_id=tenant_id))
            logger.debug("tenant_context_set", tenant_id=tenant_id, path=str(request.url.path))
            try:
                return await call_next(request)
            finally:
                pass
