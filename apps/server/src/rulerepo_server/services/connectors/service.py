"""Connector service — application-level operations for the Connector Hub.

Provides configuration, lifecycle management, and health inspection for
connectors.  This service is the primary interface used by the API layer;
it delegates to the :class:`ConnectorRegistry` for runtime state.
"""

from __future__ import annotations

import logging
from typing import Any

from rulerepo_server.core.errors import NotFoundError, ValidationError
from rulerepo_server.services.connectors.base import (
    ConnectorConfig,
    ConnectorHealth,
    EventSource,
    Sink,
)
from rulerepo_server.services.connectors.registry import ConnectorRegistry

logger = logging.getLogger(__name__)

# Known connector types and their factory callables.  Connector packages
# register themselves here at import time via ``register_connector_type``.
_CONNECTOR_FACTORIES: dict[str, type] = {}


def register_connector_type(connector_type: str, factory: type) -> None:
    """Register a connector implementation so the service can instantiate it.

    Connector packages call this at module level::

        register_connector_type("hris-smarthr", SmartHRConnector)

    Args:
        connector_type: Machine-readable identifier matching
            ``ConnectorConfig.connector_type``.
        factory: A class whose ``__init__`` accepts a
            :class:`ConnectorConfig` and produces an ``EventSource``,
            ``Sink``, or ``Connector``.
    """
    _CONNECTOR_FACTORIES[connector_type] = factory
    logger.info(
        "connector_type_registered",
        extra={"connector_type": connector_type},
    )


def available_connector_types() -> list[dict[str, str]]:
    """Return metadata about all connector types that have been registered.

    Returns:
        A list of dicts with ``connector_type`` and ``description`` keys.
    """
    results: list[dict[str, str]] = []
    for ctype, factory in _CONNECTOR_FACTORIES.items():
        results.append(
            {
                "connector_type": ctype,
                "description": getattr(factory, "__doc__", "") or "",
            }
        )
    return results


class ConnectorService:
    """Application service for managing connector lifecycle.

    Args:
        registry: The in-process connector registry.  Typically a
            singleton shared across the application.
    """

    def __init__(self, registry: ConnectorRegistry) -> None:
        self._registry = registry
        self._configs: dict[tuple[str, str], ConnectorConfig] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def configure_connector(
        self,
        tenant_id: str,
        config: ConnectorConfig,
    ) -> ConnectorConfig:
        """Configure and activate a connector for a tenant.

        Instantiates the connector from its registered factory, stores the
        configuration, and registers the instance in the runtime registry.

        Args:
            tenant_id: The owning tenant.
            config: Connector configuration.

        Returns:
            The persisted configuration (with ``tenant_id`` normalised).

        Raises:
            ValidationError: If the connector type is unknown.
        """
        if config.connector_type not in _CONNECTOR_FACTORIES:
            raise ValidationError(
                f"Unknown connector type: {config.connector_type}. Available: {sorted(_CONNECTOR_FACTORIES)}"
            )

        config.tenant_id = tenant_id
        factory = _CONNECTOR_FACTORIES[config.connector_type]

        try:
            connector: EventSource | Sink = factory(config)
        except Exception as exc:
            raise ValidationError(f"Failed to instantiate connector '{config.connector_type}': {exc}") from exc

        # If a connector with the same key exists, replace it.
        key = (tenant_id, config.connector_type)
        try:
            self._registry.unregister(tenant_id, config.connector_type)
        except NotFoundError:
            pass

        self._registry.register(tenant_id, config.connector_type, connector)
        self._configs[key] = config

        logger.info(
            "connector_configured",
            extra={
                "tenant_id": tenant_id,
                "connector_type": config.connector_type,
            },
        )
        return config

    async def remove_connector(
        self,
        tenant_id: str,
        connector_type: str,
    ) -> None:
        """Deactivate and remove a connector for a tenant.

        Args:
            tenant_id: The owning tenant.
            connector_type: The connector to remove.

        Raises:
            NotFoundError: If the connector is not configured.
        """
        self._registry.unregister(tenant_id, connector_type)
        key = (tenant_id, connector_type)
        self._configs.pop(key, None)

        logger.info(
            "connector_removed",
            extra={
                "tenant_id": tenant_id,
                "connector_type": connector_type,
            },
        )

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    async def get_connector_status(
        self,
        tenant_id: str,
        connector_type: str,
    ) -> ConnectorHealth:
        """Run a health check on a specific connector.

        Args:
            tenant_id: The owning tenant.
            connector_type: The connector to check.

        Returns:
            A :class:`ConnectorHealth` snapshot.

        Raises:
            NotFoundError: If the connector is not registered.
        """
        connector = self._registry.get(tenant_id, connector_type)
        return await connector.health_check()

    async def list_connectors(
        self,
        tenant_id: str,
    ) -> list[ConnectorConfig]:
        """List all configured connectors for a tenant.

        Args:
            tenant_id: The owning tenant.

        Returns:
            A list of :class:`ConnectorConfig` instances.
        """
        return [cfg for (tid, _), cfg in self._configs.items() if tid == tenant_id]

    async def test_connection(
        self,
        tenant_id: str,
        connector_type: str,
    ) -> ConnectorHealth:
        """Test connectivity for a connector without altering its state.

        Identical to :meth:`get_connector_status` but semantically signals
        a user-initiated probe rather than an automated check.

        Args:
            tenant_id: The owning tenant.
            connector_type: The connector to test.

        Returns:
            A :class:`ConnectorHealth` snapshot.

        Raises:
            NotFoundError: If the connector is not registered.
        """
        return await self.get_connector_status(tenant_id, connector_type)

    async def list_available_types(self) -> list[dict[str, Any]]:
        """Return all connector types that have been registered.

        Returns:
            A list of dicts with ``connector_type`` and ``description``.
        """
        return available_connector_types()
