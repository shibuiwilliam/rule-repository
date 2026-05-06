"""Tenant context management using contextvars.

Provides thread-safe and async-safe tenant context propagation.
Every request carries a TenantContext resolved from the API key.
Background workers must set tenant context explicitly via tenant_scope().
"""

from __future__ import annotations

import contextvars
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"
"""Default tenant ID used when multi-tenancy is not configured."""

_current_tenant: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar(
    "_current_tenant",
    default=None,
)


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context propagated through the request lifecycle.

    Attributes:
        tenant_id: Unique identifier for the tenant.
        tenant_name: Optional human-readable tenant name.
    """

    tenant_id: str
    tenant_name: str | None = None


def get_current_tenant() -> TenantContext | None:
    """Return the current tenant context, or None if not set.

    Returns:
        The active TenantContext, or None if no tenant is set.
    """
    return _current_tenant.get()


def set_current_tenant(tenant: TenantContext) -> contextvars.Token[TenantContext | None]:
    """Set the current tenant context.

    Args:
        tenant: The tenant context to activate.

    Returns:
        A Token that can be used to reset the context to its previous value.
    """
    return _current_tenant.set(tenant)


@contextmanager
def tenant_scope(tenant_id: str, tenant_name: str | None = None) -> Generator[TenantContext]:
    """Context manager for setting tenant scope in background workers.

    Workers don't have an HTTP request, so the tenancy middleware doesn't fire.
    Use this context manager to explicitly set tenant context.

    Args:
        tenant_id: The tenant ID to scope operations to.
        tenant_name: Optional human-readable tenant name.

    Yields:
        The active TenantContext for the duration of the scope.

    Example:
        async def my_worker_task(ctx: dict) -> None:
            with tenant_scope("tenant-123", "Acme Corp"):
                await do_tenant_scoped_work()
    """
    tenant = TenantContext(tenant_id=tenant_id, tenant_name=tenant_name)
    token = _current_tenant.set(tenant)
    try:
        yield tenant
    finally:
        _current_tenant.reset(token)
