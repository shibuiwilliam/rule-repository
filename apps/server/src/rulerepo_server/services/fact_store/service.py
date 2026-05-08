"""Fact Store service — resolves external facts that rules depend on.

The Fact Store sits between the evaluation pipeline and external data
sources.  When a rule declares ``external_facts_required`` (or embeds
fact references in its preconditions), the evaluation pipeline asks the
Fact Store to resolve those facts before invoking the LLM.

All resolution is tenant-scoped: facts are never returned across tenant
boundaries.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.errors import ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import (
    Fact,
    FactResolutionResult,
    FactSchema,
    FactStatus,
)
from rulerepo_server.domain.rule import Rule
from rulerepo_server.services.fact_store.cache import FactCache
from rulerepo_server.services.fact_store.registry import FactProviderRegistry

logger = get_logger(__name__)


class FactStore:
    """Central service for resolving external facts.

    Args:
        registry: The provider registry to dispatch fact keys.
        cache_backend: Optional cache.  If ``None``, a default
            in-memory ``FactCache`` is created.
    """

    def __init__(
        self,
        registry: FactProviderRegistry,
        cache_backend: FactCache | None = None,
    ) -> None:
        self._registry = registry
        self._cache = cache_backend or FactCache()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(
        self,
        required_facts: list[str],
        context: dict[str, Any],
        tenant_id: str,
    ) -> FactResolutionResult:
        """Resolve a batch of fact keys.

        For each key the method:
        1. Looks up the responsible provider via the registry.
        2. Checks the cache (tenant-scoped).
        3. Calls the provider if not cached.
        4. Stores the result in the cache if a TTL is set.

        Args:
            required_facts: List of canonical fact keys to resolve.
            context: Caller-supplied context (e.g., employee_id).
            tenant_id: Tenant identifier — facts never cross tenants.

        Returns:
            A ``FactResolutionResult`` summarising resolved, missing,
            and errored facts.

        Raises:
            ValidationError: If *required_facts* is empty.
        """
        if not required_facts:
            raise ValidationError("required_facts must not be empty")

        context_hash = FactCache.hash_context(context)
        resolved: dict[str, Fact] = {}
        missing: list[str] = []
        errors: dict[str, str] = {}

        for key in required_facts:
            # 1. Find provider
            provider = await self._registry.get_provider(key)
            if provider is None:
                missing.append(key)
                logger.warning("fact_no_provider", key=key, tenant_id=tenant_id)
                continue

            # 2. Check cache
            cached = await self._cache.get(key, context_hash, tenant_id)
            if cached is not None:
                resolved[key] = Fact(
                    key=cached.key,
                    value=cached.value,
                    status=FactStatus.CACHED,
                    source_provider=cached.source_provider,
                    resolved_at=cached.resolved_at,
                    ttl_seconds=cached.ttl_seconds,
                    metadata=cached.metadata,
                )
                continue

            # 3. Fetch from provider
            try:
                fact = await provider.fetch(key, context)
            except Exception as exc:
                error_msg = f"{provider.name}: {exc}"
                errors[key] = error_msg
                logger.error(
                    "fact_fetch_error",
                    key=key,
                    provider=provider.name,
                    error=str(exc),
                    tenant_id=tenant_id,
                )
                continue

            if fact is None:
                missing.append(key)
                logger.info(
                    "fact_not_found",
                    key=key,
                    provider=provider.name,
                    tenant_id=tenant_id,
                )
                continue

            resolved[key] = fact

            # 4. Cache if TTL is set
            if fact.ttl_seconds is not None and fact.ttl_seconds > 0:
                await self._cache.put(key, context_hash, tenant_id, fact)

        logger.info(
            "fact_resolution_complete",
            requested=len(required_facts),
            resolved=len(resolved),
            missing=len(missing),
            errors=len(errors),
            tenant_id=tenant_id,
        )

        return FactResolutionResult(
            requested=required_facts,
            resolved=resolved,
            missing=missing,
            errors=errors,
        )

    async def resolve_for_rule(
        self,
        rule: Rule,
        context: dict[str, Any],
        tenant_id: str,
    ) -> FactResolutionResult:
        """Resolve all external facts required by a rule.

        Reads ``rule.external_facts_required`` if present, falling back
        to scanning ``rule.preconditions`` for fact references of the
        form ``fact:<key>``.

        Args:
            rule: The rule whose facts should be resolved.
            context: Caller-supplied context.
            tenant_id: Tenant identifier.

        Returns:
            A ``FactResolutionResult``.
        """
        required: list[str] = []

        # Prefer explicit declaration if the field exists.
        explicit = getattr(rule, "external_facts_required", None)
        if explicit:
            required.extend(explicit)
        else:
            # Fall back: scan preconditions for ``fact:<key>`` patterns.
            for precondition in rule.preconditions:
                if precondition.startswith("fact:"):
                    required.append(precondition.removeprefix("fact:"))

        if not required:
            return FactResolutionResult(requested=[])

        return await self.resolve(required, context, tenant_id)

    async def invalidate_cache(
        self,
        fact_key: str,
        context: dict[str, Any] | None,
        tenant_id: str,
    ) -> None:
        """Invalidate cached entries for a fact key.

        Args:
            fact_key: The fact key to invalidate.
            context: If provided, invalidate only this context variant.
            tenant_id: Tenant identifier.
        """
        context_hash = FactCache.hash_context(context) if context is not None else None
        await self._cache.invalidate(fact_key, context_hash, tenant_id)
        logger.info(
            "fact_cache_invalidated",
            key=fact_key,
            tenant_id=tenant_id,
        )

    async def health_check(self) -> dict[str, bool]:
        """Check health of all registered providers.

        Returns:
            Dict mapping provider name to health status.
        """
        providers = await self._registry.list_providers()
        results: dict[str, bool] = {}
        for info in providers:
            provider_name = info["name"]
            provider = None
            # Locate provider instance by name.
            for p in self._registry._provider_list:
                if p.name == provider_name:
                    provider = p
                    break
            if provider is None:
                results[provider_name] = False
                continue
            try:
                results[provider_name] = await provider.health_check()
            except Exception as exc:
                logger.error(
                    "fact_provider_health_error",
                    provider=provider_name,
                    error=str(exc),
                )
                results[provider_name] = False

        return results

    async def list_supported_facts(self) -> list[FactSchema]:
        """Return all fact schemas from all registered providers.

        Returns:
            Combined list of ``FactSchema``.
        """
        return await self._registry.list_supported_facts()
