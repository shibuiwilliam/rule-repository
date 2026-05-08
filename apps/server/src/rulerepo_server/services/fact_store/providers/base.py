"""Base protocol for Fact Store providers.

Every fact provider must implement this protocol.  Providers are
registered with the ``FactProviderRegistry`` and dispatched by the
``FactStore`` service at resolution time.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rulerepo_server.domain.fact import Fact, FactSchema


@runtime_checkable
class FactProvider(Protocol):
    """Protocol that every fact provider must satisfy.

    Attributes:
        name: Unique human-readable provider name.
        domain: Business domain this provider serves (e.g., ``hr``).
    """

    name: str
    domain: str

    async def supported_facts(self) -> list[FactSchema]:
        """Return the list of fact schemas this provider can resolve.

        Returns:
            List of ``FactSchema`` descriptors.
        """
        ...

    async def fetch(self, key: str, context: dict) -> Fact | None:
        """Resolve a single fact.

        Args:
            key: The canonical fact key to resolve.
            context: Caller-supplied context (e.g., employee_id, entity_name).

        Returns:
            A ``Fact`` if the key could be resolved, or ``None`` if the
            value is not available from this provider.
        """
        ...

    async def health_check(self) -> bool:
        """Check whether the provider's upstream data source is reachable.

        Returns:
            ``True`` if healthy, ``False`` otherwise.
        """
        ...
