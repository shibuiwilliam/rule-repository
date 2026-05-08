"""Connector Hub protocols and base types.

Defines the contracts for bidirectional integration with business systems.
Connectors can act as event sources (polling external systems for changes)
and as sinks (pushing verdicts, alerts, and notifications back).

See CLAUDE.md Section 7 (Backend Architecture) for integration points.
"""

from __future__ import annotations

import enum
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class ConnectorStatus(str, enum.Enum):
    """Lifecycle status of a connector instance."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"


@dataclass(frozen=True)
class ConnectorHealth:
    """Health snapshot for a connector.

    Attributes:
        status: Current lifecycle status.
        last_checked_at: When the health check was performed.
        error_message: Human-readable error detail, if any.
        latency_ms: Round-trip latency of the health probe in milliseconds.
    """

    status: ConnectorStatus
    last_checked_at: datetime
    error_message: str | None = None
    latency_ms: float | None = None


@dataclass
class ConnectorConfig:
    """Configuration for a connector instance.

    Attributes:
        connector_type: Identifier for the connector implementation
            (e.g., ``"hris-smarthr"``, ``"crm-salesforce"``).
        tenant_id: The tenant (organization) this connector belongs to.
        credentials_ref: Opaque reference to a secrets-manager entry
            holding the actual credentials. Never store secrets inline.
        settings: Connector-specific key-value settings.
        enabled: Whether the connector is active.
    """

    connector_type: str
    tenant_id: str
    credentials_ref: str
    settings: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

# Callback type for subscription-based event delivery.
EventCallback = Callable[[list[dict[str, Any]]], Awaitable[None]]


@runtime_checkable
class EventSource(Protocol):
    """Protocol for connectors that supply events from an external system.

    Implementations poll or subscribe to a business system and return
    domain events (attendance records, deal updates, journal entries, etc.)
    normalized to a common dict structure.
    """

    @property
    def name(self) -> str:
        """Human-readable name of this connector instance."""
        ...

    @property
    def connector_type(self) -> str:
        """Machine-readable connector type identifier."""
        ...

    @property
    def domain(self) -> str:
        """Business domain this connector serves (e.g., ``"hr"``, ``"crm"``)."""
        ...

    async def poll_events(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Poll the external system for events since *since*.

        Args:
            since: Return only events after this timestamp.
            limit: Maximum number of events to return per poll.

        Returns:
            A list of normalized event dicts.
        """
        ...

    async def subscribe(self, callback: EventCallback) -> str:
        """Register a push callback and return a subscription ID.

        Args:
            callback: Async callable invoked with a batch of event dicts.

        Returns:
            An opaque subscription identifier for later unsubscription.
        """
        ...

    async def unsubscribe(self, subscription_id: str) -> None:
        """Cancel a previously registered subscription.

        Args:
            subscription_id: The ID returned by :meth:`subscribe`.
        """
        ...

    async def health_check(self) -> ConnectorHealth:
        """Probe the external system and return a health snapshot."""
        ...


@runtime_checkable
class Sink(Protocol):
    """Protocol for connectors that push results back to an external system.

    Implementations translate Rule Repository verdicts, alerts, and
    notifications into the target system's native format.
    """

    @property
    def name(self) -> str:
        """Human-readable name of this connector instance."""
        ...

    @property
    def connector_type(self) -> str:
        """Machine-readable connector type identifier."""
        ...

    async def send_verdict(self, evaluation_result: dict[str, Any]) -> bool:
        """Push an evaluation verdict to the external system.

        Args:
            evaluation_result: Normalized evaluation result dict.

        Returns:
            True if the target system accepted the payload.
        """
        ...

    async def send_alert(self, alert: dict[str, Any]) -> bool:
        """Push a compliance or operational alert.

        Args:
            alert: Normalized alert dict.

        Returns:
            True if the target system accepted the payload.
        """
        ...

    async def send_notification(self, notification: dict[str, Any]) -> bool:
        """Push a general notification.

        Args:
            notification: Normalized notification dict.

        Returns:
            True if the target system accepted the payload.
        """
        ...

    async def health_check(self) -> ConnectorHealth:
        """Probe the external system and return a health snapshot."""
        ...


@runtime_checkable
class Connector(EventSource, Sink, Protocol):
    """A bidirectional connector combining EventSource and Sink.

    Most production connectors implement this combined protocol so that
    they can both ingest events and push results back through a single
    authenticated session.
    """
