"""SCIM 2.0 provisioning endpoints.

Provides RFC 7644 compliant endpoints for user and group provisioning.
Identity providers (Okta, Azure AD, Google Workspace) push directory
changes here so the Rule Repository stays in sync.

The tenant_id is derived from the authenticated bearer token, NEVER
from the request body or URL path.

SCIM paths:
  /scim/v2/Users          — list / create users
  /scim/v2/Users/{id}     — get / replace / patch / deactivate users
  /scim/v2/Groups         — list / create groups
  /scim/v2/Groups/{id}    — get / replace / patch / delete groups
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from rulerepo_server.core.logging import get_logger
from rulerepo_server.core.tenancy.context import require_tenant
from rulerepo_server.services.identity.scim import (
    SCIMGroup,
    SCIMListResponse,
    SCIMService,
    SCIMUser,
)

logger = get_logger(__name__)

router = APIRouter(tags=["scim"])

# ---------------------------------------------------------------------------
# Singleton service instance (replaced by DI container in production)
# ---------------------------------------------------------------------------

_scim_service = SCIMService()


def _get_scim_service() -> SCIMService:
    return _scim_service


def _resolve_tenant_id() -> str:
    """Extract tenant_id from the request context.

    SCIM endpoints MUST authenticate via bearer token. The tenant_id
    comes from the token claims, never from the URL or body.

    Returns:
        The tenant_id from the current tenant context.

    Raises:
        AuthenticationError: If no tenant context is set.
    """
    ctx = require_tenant()
    return ctx.tenant_id


# ---------------------------------------------------------------------------
# Content-Type constant
# ---------------------------------------------------------------------------

SCIM_CONTENT_TYPE = "application/scim+json"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/scim/v2/Users", response_model=SCIMListResponse)
async def list_users(
    filter: str | None = Query(default=None, description="SCIM filter expression"),
    start_index: int = Query(default=1, ge=1, alias="startIndex", description="1-based start index"),
    count: int = Query(default=100, ge=1, le=1000, description="Page size"),
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMListResponse:
    """List users with optional filtering and pagination."""
    tenant_id = _resolve_tenant_id()
    return await service.list_users(tenant_id, filter_expr=filter, start_index=start_index, count=count)


@router.post("/scim/v2/Users", response_model=SCIMUser, status_code=201)
async def create_user(
    body: SCIMUser,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMUser:
    """Provision a new user."""
    tenant_id = _resolve_tenant_id()
    return await service.create_user(tenant_id, body)


@router.get("/scim/v2/Users/{user_id}", response_model=SCIMUser)
async def get_user(
    user_id: str,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMUser:
    """Get a user by ID."""
    tenant_id = _resolve_tenant_id()
    return await service.get_user(tenant_id, user_id)


@router.put("/scim/v2/Users/{user_id}", response_model=SCIMUser)
async def replace_user(
    user_id: str,
    body: SCIMUser,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMUser:
    """Replace a user's attributes (full update)."""
    tenant_id = _resolve_tenant_id()
    return await service.update_user(tenant_id, user_id, body)


@router.patch("/scim/v2/Users/{user_id}", response_model=SCIMUser)
async def patch_user(
    user_id: str,
    body: SCIMUser,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMUser:
    """Partially update a user's attributes.

    SCIM PATCH operations are complex (RFC 7644 §3.5.2). This
    simplified implementation treats PATCH as a full replacement
    of provided fields. A full PatchOp parser is deferred.
    """
    tenant_id = _resolve_tenant_id()
    return await service.update_user(tenant_id, user_id, body)


@router.delete("/scim/v2/Users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    service: SCIMService = Depends(_get_scim_service),
) -> None:
    """Deactivate a user (SCIM DELETE = soft-delete)."""
    tenant_id = _resolve_tenant_id()
    await service.delete_user(tenant_id, user_id)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


@router.get("/scim/v2/Groups", response_model=SCIMListResponse)
async def list_groups(
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMListResponse:
    """List all groups for the tenant."""
    tenant_id = _resolve_tenant_id()
    return await service.list_groups(tenant_id)


@router.post("/scim/v2/Groups", response_model=SCIMGroup, status_code=201)
async def create_group(
    body: SCIMGroup,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMGroup:
    """Provision a new group."""
    tenant_id = _resolve_tenant_id()
    return await service.create_group(tenant_id, body)


@router.get("/scim/v2/Groups/{group_id}", response_model=SCIMGroup)
async def get_group(
    group_id: str,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMGroup:
    """Get a group by ID."""
    tenant_id = _resolve_tenant_id()
    return await service.get_group(tenant_id, group_id)


@router.put("/scim/v2/Groups/{group_id}", response_model=SCIMGroup)
async def replace_group(
    group_id: str,
    body: SCIMGroup,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMGroup:
    """Replace a group's attributes."""
    tenant_id = _resolve_tenant_id()
    return await service.update_group(tenant_id, group_id, body)


@router.patch("/scim/v2/Groups/{group_id}", response_model=SCIMGroup)
async def patch_group(
    group_id: str,
    body: SCIMGroup,
    service: SCIMService = Depends(_get_scim_service),
) -> SCIMGroup:
    """Partially update a group."""
    tenant_id = _resolve_tenant_id()
    return await service.update_group(tenant_id, group_id, body)


@router.delete("/scim/v2/Groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    service: SCIMService = Depends(_get_scim_service),
) -> None:
    """Delete a group."""
    tenant_id = _resolve_tenant_id()
    await service.delete_group(tenant_id, group_id)
