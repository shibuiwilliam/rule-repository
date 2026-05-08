"""REST API routes for the Fact Store.

Exposes endpoints for listing providers, resolving facts, checking
provider health, and invalidating the fact cache.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.fact_store.providers.employee_attributes import (
    EmployeeAttributesProvider,
)
from rulerepo_server.services.fact_store.providers.internal_master_data import (
    InternalMasterDataProvider,
)
from rulerepo_server.services.fact_store.providers.ofac_sanctions import (
    OFACSanctionsProvider,
)
from rulerepo_server.services.fact_store.providers.regulatory_feed import (
    RegulatoryFeedProvider,
)
from rulerepo_server.services.fact_store.registry import FactProviderRegistry
from rulerepo_server.services.fact_store.service import FactStore

logger = get_logger(__name__)

router = APIRouter(prefix="/facts", tags=["facts"])

# ---------------------------------------------------------------------------
# Singleton wiring — in production this would come from a DI container.
# ---------------------------------------------------------------------------

_fact_store: FactStore | None = None


def _get_fact_store() -> FactStore:
    """Lazy-initialise and return the singleton ``FactStore``."""
    global _fact_store
    if _fact_store is None:
        registry = FactProviderRegistry()
        registry.register(EmployeeAttributesProvider())
        registry.register(OFACSanctionsProvider())
        registry.register(InternalMasterDataProvider())
        registry.register(RegulatoryFeedProvider())
        _fact_store = FactStore(registry=registry)
    return _fact_store


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class FactSchemaResponse(BaseModel):
    """Schema descriptor for a resolvable fact."""

    key: str
    description: str
    value_type: str
    required_context_keys: list[str] = Field(default_factory=list)
    domain: str = "general"


class ProviderInfo(BaseModel):
    """Summary of a registered fact provider."""

    name: str
    domain: str


class ProvidersResponse(BaseModel):
    """Response for the list-providers endpoint."""

    providers: list[ProviderInfo]
    supported_facts: list[FactSchemaResponse]


class ResolveRequest(BaseModel):
    """Request body for fact resolution."""

    required_facts: list[str] = Field(..., min_length=1, description="Canonical fact keys to resolve.")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context for resolution (e.g., employee_id, entity_name).",
    )
    tenant_id: str = Field(..., min_length=1, description="Tenant identifier for isolation.")


class ResolvedFactResponse(BaseModel):
    """A single resolved fact in the response."""

    key: str
    value: Any
    status: str
    source_provider: str
    resolved_at: str
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolveResponse(BaseModel):
    """Response for the resolve endpoint."""

    requested: list[str]
    resolved: dict[str, ResolvedFactResponse]
    missing: list[str]
    errors: dict[str, str]


class HealthResponse(BaseModel):
    """Response for the health endpoint."""

    providers: dict[str, bool]


class CacheInvalidateRequest(BaseModel):
    """Request body for cache invalidation."""

    fact_key: str = Field(..., description="Fact key to invalidate.")
    context: dict[str, Any] | None = Field(
        default=None,
        description="If provided, invalidate only this context variant.",
    )
    tenant_id: str = Field(..., min_length=1, description="Tenant identifier.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers(
    store: FactStore = Depends(_get_fact_store),
) -> ProvidersResponse:
    """List all registered fact providers and their supported facts."""
    providers = await store._registry.list_providers()
    schemas = await store.list_supported_facts()

    return ProvidersResponse(
        providers=[ProviderInfo(**p) for p in providers],
        supported_facts=[
            FactSchemaResponse(
                key=s.key,
                description=s.description,
                value_type=s.value_type,
                required_context_keys=s.required_context_keys,
                domain=s.domain,
            )
            for s in schemas
        ],
    )


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_facts(
    body: ResolveRequest,
    store: FactStore = Depends(_get_fact_store),
) -> ResolveResponse:
    """Resolve a set of facts given context.

    Facts are tenant-scoped and will never cross tenant boundaries.
    """
    result = await store.resolve(
        required_facts=body.required_facts,
        context=body.context,
        tenant_id=body.tenant_id,
    )

    resolved_response: dict[str, ResolvedFactResponse] = {}
    for key, fact in result.resolved.items():
        resolved_response[key] = ResolvedFactResponse(
            key=fact.key,
            value=fact.value,
            status=fact.status.value,
            source_provider=fact.source_provider,
            resolved_at=fact.resolved_at.isoformat(),
            ttl_seconds=fact.ttl_seconds,
            metadata=fact.metadata,
        )

    return ResolveResponse(
        requested=result.requested,
        resolved=resolved_response,
        missing=result.missing,
        errors=result.errors,
    )


@router.get("/health", response_model=HealthResponse)
async def provider_health(
    store: FactStore = Depends(_get_fact_store),
) -> HealthResponse:
    """Check health status of all registered fact providers."""
    results = await store.health_check()
    return HealthResponse(providers=results)


@router.delete("/cache", status_code=204)
async def invalidate_cache(
    body: CacheInvalidateRequest,
    store: FactStore = Depends(_get_fact_store),
) -> None:
    """Invalidate cached fact entries.

    If ``context`` is provided, only the specific context variant is
    invalidated.  Otherwise all cached entries for the fact key within
    the tenant are cleared.
    """
    await store.invalidate_cache(
        fact_key=body.fact_key,
        context=body.context,
        tenant_id=body.tenant_id,
    )
