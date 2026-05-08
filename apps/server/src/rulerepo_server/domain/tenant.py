"""Multi-tenancy and identity domain types.

Pure domain — no imports from services/, adapters/, or api/.
See PROJECT.md §5.6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

_UTC = UTC


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TenantStatus(StrEnum):
    """Lifecycle status of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPROVISIONING = "deprovisioning"


class PrincipalKind(StrEnum):
    """Kind of authenticated principal."""

    USER = "user"
    SERVICE_ACCOUNT = "service_account"


# ---------------------------------------------------------------------------
# Tenant value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TenantSettings:
    """Configuration knobs scoped to a single tenant.

    Attributes:
        data_residency_region: Cloud region where tenant data is stored.
        llm_region: Region for LLM inference calls.
        llm_budget_monthly_usd: Optional monthly spend cap on LLM inference.
        encryption_key_id: Customer-managed encryption key ARN/URI.
        active_plugins: Enabled plugin identifiers for this tenant.
        default_classification: Default classification for new rules.
        audit_worm_enabled: Whether WORM audit mirroring is active.
    """

    data_residency_region: str = "us"
    llm_region: str = "us"
    llm_budget_monthly_usd: float | None = None
    encryption_key_id: str | None = None
    active_plugins: list[str] = field(default_factory=list)
    default_classification: str = "internal"
    audit_worm_enabled: bool = False


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tenant:
    """A tenant — the top-level isolation boundary for all business data.

    Every rule, evaluation, department, and audit entry belongs to exactly
    one tenant.  Tenant IDs propagate through the request context and are
    enforced at the data layer via RLS.
    """

    id: str
    name: str
    slug: str
    status: TenantStatus = TenantStatus.ACTIVE
    settings: TenantSettings = field(default_factory=TenantSettings)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))


@dataclass(frozen=True)
class Organization:
    """A legal entity within a tenant.

    Large enterprises may operate multiple legal entities (subsidiaries)
    under one tenant.  The organization links rules and departments to
    the correct legal context.
    """

    id: str
    tenant_id: str
    name: str
    legal_entity_name: str
    country_code: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))


# ---------------------------------------------------------------------------
# Identity primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Principal:
    """An authenticated actor — human user or service account.

    Carries the identity, clearance, and organizational memberships needed
    for ABAC and RLS enforcement throughout a request.
    """

    id: str
    tenant_id: str
    kind: PrincipalKind
    display_name: str
    email: str | None = None
    department_ids: list[str] = field(default_factory=list)
    clearance: str = "internal"
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    organization_id: str | None = None


@dataclass(frozen=True)
class ServiceAccount:
    """A non-human principal used for system integrations and agents.

    API key hashes are stored, never the raw key.  Scopes restrict the
    set of API operations the service account may invoke.
    """

    id: str
    tenant_id: str
    name: str
    scopes: list[str] = field(default_factory=list)
    api_key_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))
    expires_at: datetime | None = None


@dataclass(frozen=True)
class Group:
    """A named collection of principals within a tenant.

    Groups are typically synced from an identity provider via SCIM.
    """

    id: str
    tenant_id: str
    name: str
    member_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Role:
    """A named set of permissions, optionally scoped to a domain.

    Roles are assigned to principals and evaluated by the ABAC engine.
    A None domain means the role applies globally within the tenant.
    """

    name: str
    permissions: list[str] = field(default_factory=list)
    domain: str | None = None
