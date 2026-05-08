"""Tenant isolation middleware — sets tenant context per request.

Extracts tenant identity from JWT tokens, API keys, or the X-Tenant-ID
header and sets the request-scoped tenant context.  In single-tenant
mode (default), uses DEFAULT_TENANT_ID for all requests.

See CLAUDE.md §14.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger
from rulerepo_server.core.tenancy.context import (
    DEFAULT_TENANT_ID,
    TenantContext,
    set_current_tenant,
)
from rulerepo_server.domain.tenant import Principal, PrincipalKind, TenantStatus

logger = get_logger(__name__)

# Paths that bypass tenant resolution (health checks, OpenAPI docs, SCIM).
_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/health", "/readiness")


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Sets tenant context for each request based on configuration mode.

    In single-tenant mode (default): all requests use DEFAULT_TENANT_ID
    with an anonymous principal.

    In multi-tenant mode: tenant_id is resolved from:
      1. A validated JWT ``tid`` claim (preferred).
      2. An API-key lookup that maps to a tenant.
      3. The ``X-Tenant-ID`` header (lowest trust — for dev/testing only).

    The middleware also validates that the resolved tenant exists and is
    ACTIVE.  SUSPENDED or DEPROVISIONING tenants receive a 403.
    """

    def __init__(self, app, tenant_store=None):
        """Initialise the middleware.

        Args:
            app: The ASGI application.
            tenant_store: Optional callable ``async (tenant_id) -> Tenant | None``
                          used to validate tenant existence and status.
                          When None, validation is skipped (dev mode).
        """
        super().__init__(app)
        self._tenant_store = tenant_store

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request, setting tenant context."""
        # Skip tenant resolution for exempt paths
        path = request.url.path
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            set_current_tenant(TenantContext(tenant_id=DEFAULT_TENANT_ID, tenant_name="default"))
            return await call_next(request)

        settings = get_settings()
        multi_tenant = getattr(settings, "multi_tenant_enabled", False)

        if not multi_tenant:
            return await self._single_tenant_dispatch(request, call_next)

        return await self._multi_tenant_dispatch(request, call_next)

    # ------------------------------------------------------------------
    # Internal dispatch modes
    # ------------------------------------------------------------------

    async def _single_tenant_dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Single-tenant mode: every request uses the default tenant."""
        principal = Principal(
            id="anonymous",
            tenant_id=DEFAULT_TENANT_ID,
            kind=PrincipalKind.USER,
            display_name="Anonymous",
            clearance="internal",
            roles=["owner"],
        )
        set_current_tenant(
            TenantContext(
                tenant_id=DEFAULT_TENANT_ID,
                tenant_name="default",
                principal=principal,
            )
        )
        return await call_next(request)

    async def _multi_tenant_dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Multi-tenant mode: resolve tenant from auth artifacts."""
        tenant_id: str | None = None
        principal: Principal | None = None

        # 1. Try JWT (set by upstream auth middleware / gateway)
        jwt_tenant = request.state.__dict__.get("jwt_tenant_id") if hasattr(request, "state") else None
        jwt_principal = request.state.__dict__.get("jwt_principal") if hasattr(request, "state") else None
        if jwt_tenant:
            tenant_id = jwt_tenant
            principal = jwt_principal

        # 2. Try API-key header (resolved by auth dependency, stashed on state)
        if not tenant_id:
            api_key_tenant = request.state.__dict__.get("api_key_tenant_id") if hasattr(request, "state") else None
            api_key_principal = request.state.__dict__.get("api_key_principal") if hasattr(request, "state") else None
            if api_key_tenant:
                tenant_id = api_key_tenant
                principal = api_key_principal

        # 3. Fallback: X-Tenant-ID header (dev/testing only)
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            tenant_id = DEFAULT_TENANT_ID

        # Build a minimal principal if none was resolved
        if principal is None:
            principal = Principal(
                id="anonymous",
                tenant_id=tenant_id,
                kind=PrincipalKind.USER,
                display_name="Anonymous",
                clearance="internal",
            )

        # Validate tenant status if store is available
        if self._tenant_store is not None:
            tenant = await self._tenant_store(tenant_id)
            if tenant is None:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Unknown tenant", "code": "TENANT_NOT_FOUND"},
                )
            if tenant.status == TenantStatus.SUSPENDED:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Tenant is suspended", "code": "TENANT_SUSPENDED"},
                )
            if tenant.status == TenantStatus.DEPROVISIONING:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Tenant is being deprovisioned",
                        "code": "TENANT_DEPROVISIONING",
                    },
                )
            tenant_name = tenant.name
        else:
            tenant_name = None

        set_current_tenant(TenantContext(tenant_id=tenant_id, tenant_name=tenant_name, principal=principal))
        logger.debug("tenant_context_set", tenant_id=tenant_id, path=str(request.url.path))
        return await call_next(request)
