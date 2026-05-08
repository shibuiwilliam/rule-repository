"""REST API routes for tenant management.

Tenant CRUD and settings are restricted to platform administrators.
The tenant_id for data-bearing operations is NEVER read from the
request body — it is always derived from the authenticated principal's
context.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from rulerepo_server.core.auth import CurrentUser, Role, get_current_user, require_role
from rulerepo_server.domain.tenant import TenantSettings
from rulerepo_server.services.tenancy.service import TenantService

router = APIRouter(tags=["tenants"])

# ---------------------------------------------------------------------------
# Singleton service instance (replaced by DI container in production)
# ---------------------------------------------------------------------------

_tenant_service = TenantService()


def _get_tenant_service() -> TenantService:
    return _tenant_service


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class TenantSettingsSchema(BaseModel):
    """Pydantic schema for tenant settings."""

    data_residency_region: str = "us"
    llm_region: str = "us"
    llm_budget_monthly_usd: float | None = None
    encryption_key_id: str | None = None
    active_plugins: list[str] = Field(default_factory=list)
    default_classification: str = "internal"
    audit_worm_enabled: bool = False


class TenantCreateRequest(BaseModel):
    """Request body for creating a tenant."""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    slug: str = Field(
        ...,
        min_length=3,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$",
        description="URL-safe slug",
    )
    settings: TenantSettingsSchema = Field(default_factory=TenantSettingsSchema)


class TenantSettingsUpdateRequest(BaseModel):
    """Request body for updating tenant settings."""

    settings: TenantSettingsSchema


class TenantResponse(BaseModel):
    """Response schema for a tenant."""

    id: str
    name: str
    slug: str
    status: str
    settings: TenantSettingsSchema
    created_at: str
    updated_at: str


class TenantListResponse(BaseModel):
    """Response schema for listing tenants."""

    tenants: list[TenantResponse]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenant_to_response(tenant) -> dict:
    """Convert a domain Tenant to a response dict."""
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status.value,
        "settings": {
            "data_residency_region": tenant.settings.data_residency_region,
            "llm_region": tenant.settings.llm_region,
            "llm_budget_monthly_usd": tenant.settings.llm_budget_monthly_usd,
            "encryption_key_id": tenant.settings.encryption_key_id,
            "active_plugins": tenant.settings.active_plugins,
            "default_classification": tenant.settings.default_classification,
            "audit_worm_enabled": tenant.settings.audit_worm_enabled,
        },
        "created_at": tenant.created_at.isoformat(),
        "updated_at": tenant.updated_at.isoformat(),
    }


def _schema_to_settings(schema: TenantSettingsSchema) -> TenantSettings:
    """Convert a Pydantic settings schema to a domain TenantSettings."""
    return TenantSettings(
        data_residency_region=schema.data_residency_region,
        llm_region=schema.llm_region,
        llm_budget_monthly_usd=schema.llm_budget_monthly_usd,
        encryption_key_id=schema.encryption_key_id,
        active_plugins=schema.active_plugins,
        default_classification=schema.default_classification,
        audit_worm_enabled=schema.audit_worm_enabled,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    body: TenantCreateRequest,
    _user: CurrentUser = Depends(require_role(Role.OWNER)),
    service: TenantService = Depends(_get_tenant_service),
) -> dict:
    """Create a new tenant.

    Restricted to platform administrators (OWNER role).
    """
    settings = _schema_to_settings(body.settings)
    tenant = await service.create_tenant(name=body.name, slug=body.slug, settings=settings)
    return _tenant_to_response(tenant)


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    _user: CurrentUser = Depends(get_current_user),
    service: TenantService = Depends(_get_tenant_service),
) -> dict:
    """Get a tenant by ID."""
    tenant = await service.get_tenant(tenant_id)
    return _tenant_to_response(tenant)


@router.patch("/tenants/{tenant_id}/settings", response_model=TenantResponse)
async def update_tenant_settings(
    tenant_id: str,
    body: TenantSettingsUpdateRequest,
    _user: CurrentUser = Depends(require_role(Role.OWNER)),
    service: TenantService = Depends(_get_tenant_service),
) -> dict:
    """Update tenant settings.

    Restricted to platform administrators (OWNER role).
    """
    settings = _schema_to_settings(body.settings)
    tenant = await service.update_tenant_settings(tenant_id, settings)
    return _tenant_to_response(tenant)


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    _user: CurrentUser = Depends(require_role(Role.OWNER)),
    service: TenantService = Depends(_get_tenant_service),
) -> dict:
    """List all tenants.

    Restricted to platform administrators (OWNER role).
    """
    tenants = await service.list_tenants()
    return {
        "tenants": [_tenant_to_response(t) for t in tenants],
        "total": len(tenants),
    }
