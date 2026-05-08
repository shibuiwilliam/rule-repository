"""Tenant lifecycle management service.

Handles CRUD for tenants and organizations.  Tenant IDs are the
top-level isolation boundary for all business data.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.tenant import (
    Organization,
    Tenant,
    TenantSettings,
    TenantStatus,
)

logger = get_logger(__name__)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$")


class TenantService:
    """Manages the tenant and organization lifecycle.

    In a production deployment this service delegates to the PostgreSQL
    ``tenants`` and ``organizations`` tables.  For Phase 7a the service
    uses an in-memory store so the domain logic can be validated before
    the persistence layer is wired.

    Args:
        store: Optional backing store mapping tenant_id -> Tenant.
               Defaults to an empty in-memory dict.
        org_store: Optional backing store mapping org_id -> Organization.
    """

    def __init__(
        self,
        store: dict[str, Tenant] | None = None,
        org_store: dict[str, Organization] | None = None,
    ) -> None:
        self._tenants: dict[str, Tenant] = store if store is not None else {}
        self._organizations: dict[str, Organization] = org_store if org_store is not None else {}
        # Secondary index: slug -> tenant_id
        self._slug_index: dict[str, str] = {t.slug: t.id for t in self._tenants.values()}

    # ------------------------------------------------------------------
    # Tenant CRUD
    # ------------------------------------------------------------------

    async def create_tenant(
        self,
        name: str,
        slug: str,
        settings: TenantSettings | None = None,
    ) -> Tenant:
        """Create a new tenant.

        Args:
            name: Human-readable tenant name.
            slug: URL-safe identifier (lowercase alphanumeric + hyphens, 3-63 chars).
            settings: Optional tenant-level configuration.

        Returns:
            The created Tenant.

        Raises:
            ValidationError: If the slug is malformed.
            ConflictError: If the slug is already taken.
        """
        if not _SLUG_RE.match(slug):
            raise ValidationError(f"Slug must be 3-63 lowercase alphanumeric characters or hyphens: '{slug}'")
        if slug in self._slug_index:
            raise ConflictError(f"Tenant slug already exists: '{slug}'")

        now = datetime.now(tz=UTC)
        tenant = Tenant(
            id=str(uuid4()),
            name=name,
            slug=slug,
            status=TenantStatus.ACTIVE,
            settings=settings or TenantSettings(),
            created_at=now,
            updated_at=now,
        )
        self._tenants[tenant.id] = tenant
        self._slug_index[tenant.slug] = tenant.id
        logger.info("tenant_created", tenant_id=tenant.id, slug=slug)
        return tenant

    async def get_tenant(self, tenant_id: str) -> Tenant:
        """Get a tenant by ID.

        Args:
            tenant_id: The tenant's unique identifier.

        Returns:
            The Tenant.

        Raises:
            NotFoundError: If the tenant does not exist.
        """
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant", tenant_id)
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """Get a tenant by its URL slug.

        Args:
            slug: The tenant's slug.

        Returns:
            The Tenant.

        Raises:
            NotFoundError: If no tenant with that slug exists.
        """
        tenant_id = self._slug_index.get(slug)
        if tenant_id is None:
            raise NotFoundError("Tenant", slug)
        return self._tenants[tenant_id]

    async def list_tenants(self) -> list[Tenant]:
        """List all tenants, ordered by name.

        Returns:
            All tenants sorted alphabetically by name.
        """
        return sorted(self._tenants.values(), key=lambda t: t.name)

    async def update_tenant_settings(
        self,
        tenant_id: str,
        settings: TenantSettings,
    ) -> Tenant:
        """Replace the settings for a tenant.

        Args:
            tenant_id: The tenant to update.
            settings: The new settings.

        Returns:
            The updated Tenant.

        Raises:
            NotFoundError: If the tenant does not exist.
        """
        existing = await self.get_tenant(tenant_id)
        updated = Tenant(
            id=existing.id,
            name=existing.name,
            slug=existing.slug,
            status=existing.status,
            settings=settings,
            created_at=existing.created_at,
            updated_at=datetime.now(tz=UTC),
        )
        self._tenants[tenant_id] = updated
        logger.info("tenant_settings_updated", tenant_id=tenant_id)
        return updated

    async def suspend_tenant(self, tenant_id: str) -> Tenant:
        """Suspend a tenant, blocking all API access.

        Args:
            tenant_id: The tenant to suspend.

        Returns:
            The updated Tenant with SUSPENDED status.

        Raises:
            NotFoundError: If the tenant does not exist.
        """
        existing = await self.get_tenant(tenant_id)
        updated = Tenant(
            id=existing.id,
            name=existing.name,
            slug=existing.slug,
            status=TenantStatus.SUSPENDED,
            settings=existing.settings,
            created_at=existing.created_at,
            updated_at=datetime.now(tz=UTC),
        )
        self._tenants[tenant_id] = updated
        logger.info("tenant_suspended", tenant_id=tenant_id)
        return updated

    # ------------------------------------------------------------------
    # Organization CRUD
    # ------------------------------------------------------------------

    async def create_organization(
        self,
        tenant_id: str,
        name: str,
        legal_entity_name: str,
        country_code: str,
    ) -> Organization:
        """Create an organization within a tenant.

        Args:
            tenant_id: The owning tenant.
            name: Human-readable name.
            legal_entity_name: Full legal entity name.
            country_code: ISO 3166-1 alpha-2 country code.

        Returns:
            The created Organization.

        Raises:
            NotFoundError: If the tenant does not exist.
        """
        await self.get_tenant(tenant_id)  # validate tenant exists
        org = Organization(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name=name,
            legal_entity_name=legal_entity_name,
            country_code=country_code.upper(),
        )
        self._organizations[org.id] = org
        logger.info("organization_created", org_id=org.id, tenant_id=tenant_id)
        return org

    async def get_organization(self, org_id: str) -> Organization:
        """Get an organization by ID.

        Raises:
            NotFoundError: If the organization does not exist.
        """
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("Organization", org_id)
        return org

    async def list_organizations(self, tenant_id: str) -> list[Organization]:
        """List all organizations for a tenant."""
        return sorted(
            (o for o in self._organizations.values() if o.tenant_id == tenant_id),
            key=lambda o: o.name,
        )
