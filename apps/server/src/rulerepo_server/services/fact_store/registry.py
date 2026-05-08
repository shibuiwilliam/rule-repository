"""Fact provider registry.

Maintains a mapping from fact keys to the providers that can resolve
them.  The ``FactStore`` service uses the registry to dispatch
resolution requests.
"""

from __future__ import annotations

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import FactSchema
from rulerepo_server.services.fact_store.providers.base import FactProvider

logger = get_logger(__name__)


class FactProviderRegistry:
    """Registry of fact providers keyed by the fact keys they support.

    Thread-safety note: registration is expected to happen at startup,
    before concurrent request handling begins.
    """

    def __init__(self) -> None:
        self._providers: dict[str, FactProvider] = {}
        self._provider_list: list[FactProvider] = []

    def register(self, provider: FactProvider) -> None:
        """Register a provider and index its supported fact keys.

        If a fact key is already claimed by another provider, the new
        registration wins and a warning is logged.

        Args:
            provider: The provider instance to register.
        """
        if provider not in self._provider_list:
            self._provider_list.append(provider)

        # We need to index synchronously at registration time.
        # Providers declare their schemas eagerly here; the async
        # ``supported_facts()`` call is used for runtime introspection.
        logger.info(
            "fact_provider_registered",
            provider=provider.name,
            domain=provider.domain,
        )

    async def _ensure_indexed(self, provider: FactProvider) -> None:
        """Lazily index a provider's fact keys on first use."""
        schemas = await provider.supported_facts()
        for schema in schemas:
            existing = self._providers.get(schema.key)
            if existing is not None and existing is not provider:
                logger.warning(
                    "fact_key_override",
                    key=schema.key,
                    old_provider=existing.name,
                    new_provider=provider.name,
                )
            self._providers[schema.key] = provider

    async def _ensure_all_indexed(self) -> None:
        """Ensure every registered provider has been indexed."""
        for provider in self._provider_list:
            await self._ensure_indexed(provider)

    async def get_provider(self, fact_key: str) -> FactProvider | None:
        """Find the provider that handles *fact_key*.

        Args:
            fact_key: The canonical fact key.

        Returns:
            The provider, or ``None`` if no provider handles this key.
        """
        await self._ensure_all_indexed()
        return self._providers.get(fact_key)

    async def list_providers(self) -> list[dict[str, str]]:
        """Return summary information for all registered providers.

        Returns:
            List of dicts with ``name`` and ``domain`` keys.
        """
        return [{"name": p.name, "domain": p.domain} for p in self._provider_list]

    async def list_supported_facts(self) -> list[FactSchema]:
        """Aggregate all fact schemas from all registered providers.

        Returns:
            Combined list of ``FactSchema`` from every provider.
        """
        schemas: list[FactSchema] = []
        for provider in self._provider_list:
            schemas.extend(await provider.supported_facts())
        return schemas
