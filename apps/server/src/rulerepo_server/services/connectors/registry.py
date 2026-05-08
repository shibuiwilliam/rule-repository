"""Connector registry — runtime catalogue of active connector instances.

The registry indexes connectors by ``(tenant_id, connector_type)`` and
provides lookup, lifecycle, and health-check operations.  It is the
single point of truth the rest of the application uses to obtain a
connector reference.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC
from typing import Any

from rulerepo_server.core.errors import ConflictError, NotFoundError
from rulerepo_server.services.connectors.base import (
    Connector,
    ConnectorHealth,
    ConnectorStatus,
    EventSource,
    Sink,
)

logger = logging.getLogger(__name__)

# Registry key is (tenant_id, connector_type).
_RegistryKey = tuple[str, str]


class ConnectorRegistry:
    """In-process registry of active connector instances.

    Thread-safety note: the registry is designed for single-process
    async servers.  If the application runs multi-worker, each worker
    holds its own registry and connector instances.

    Attributes:
        _connectors: Mapping from (tenant_id, connector_type) to the
            connector instance (which may be EventSource, Sink, or both).
    """

    def __init__(self) -> None:
        self._connectors: dict[_RegistryKey, EventSource | Sink | Connector] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        tenant_id: str,
        connector_type: str,
        connector: EventSource | Sink | Connector,
    ) -> None:
        """Register a connector instance for a tenant.

        Args:
            tenant_id: The owning tenant.
            connector_type: Machine-readable connector identifier.
            connector: The connector instance.

        Raises:
            ConflictError: If a connector with the same key already exists.
        """
        key: _RegistryKey = (tenant_id, connector_type)
        if key in self._connectors:
            raise ConflictError(f"Connector '{connector_type}' already registered for tenant '{tenant_id}'")
        self._connectors[key] = connector
        logger.info(
            "connector_registered",
            extra={"tenant_id": tenant_id, "connector_type": connector_type},
        )

    def unregister(self, tenant_id: str, connector_type: str) -> None:
        """Remove a connector from the registry.

        Args:
            tenant_id: The owning tenant.
            connector_type: Machine-readable connector identifier.

        Raises:
            NotFoundError: If no matching connector is registered.
        """
        key: _RegistryKey = (tenant_id, connector_type)
        if key not in self._connectors:
            raise NotFoundError("Connector", f"{tenant_id}/{connector_type}")
        del self._connectors[key]
        logger.info(
            "connector_unregistered",
            extra={"tenant_id": tenant_id, "connector_type": connector_type},
        )

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(
        self,
        tenant_id: str,
        connector_type: str,
    ) -> EventSource | Sink | Connector:
        """Retrieve a connector by tenant and type.

        Args:
            tenant_id: The owning tenant.
            connector_type: Machine-readable connector identifier.

        Returns:
            The registered connector instance.

        Raises:
            NotFoundError: If no matching connector is registered.
        """
        key: _RegistryKey = (tenant_id, connector_type)
        connector = self._connectors.get(key)
        if connector is None:
            raise NotFoundError("Connector", f"{tenant_id}/{connector_type}")
        return connector

    def list_for_tenant(
        self,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """List all connectors registered for a tenant.

        Args:
            tenant_id: The owning tenant.

        Returns:
            A list of dicts with ``connector_type`` and ``name`` keys.
        """
        results: list[dict[str, Any]] = []
        for (tid, ctype), connector in self._connectors.items():
            if tid == tenant_id:
                results.append(
                    {
                        "connector_type": ctype,
                        "name": getattr(connector, "name", ctype),
                        "domain": getattr(connector, "domain", "unknown"),
                    }
                )
        return results

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check_all(
        self,
        tenant_id: str,
    ) -> dict[str, ConnectorHealth]:
        """Run health checks on all connectors for a tenant concurrently.

        Args:
            tenant_id: The owning tenant.

        Returns:
            Mapping of connector_type to its ConnectorHealth result.
        """
        targets: dict[str, EventSource | Sink | Connector] = {}
        for (tid, ctype), connector in self._connectors.items():
            if tid == tenant_id:
                targets[ctype] = connector

        if not targets:
            return {}

        async def _check(ctype: str, conn: EventSource | Sink | Connector) -> tuple[str, ConnectorHealth]:
            try:
                health = await conn.health_check()
            except Exception as exc:
                from datetime import datetime

                health = ConnectorHealth(
                    status=ConnectorStatus.ERROR,
                    last_checked_at=datetime.now(UTC),
                    error_message=str(exc),
                )
            return ctype, health

        results = await asyncio.gather(*[_check(ct, c) for ct, c in targets.items()])
        return dict(results)
