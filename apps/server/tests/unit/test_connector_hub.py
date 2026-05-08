"""Unit tests for the Connector Hub (workstream 7f).

Tests connector protocols, registry, service, and reference connectors.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from rulerepo_server.services.connectors.base import (
    ConnectorConfig,
    ConnectorHealth,
    ConnectorStatus,
)
from rulerepo_server.services.connectors.registry import ConnectorRegistry

# ---------------------------------------------------------------------------
# Mock connector for testing
# ---------------------------------------------------------------------------


class MockConnector:
    """A test connector implementing EventSource + Sink."""

    name = "mock_connector"
    connector_type = "test_mock"
    domain = "test"

    def __init__(self) -> None:
        self._healthy = True
        self._events_sent: list[dict] = []

    async def poll_events(self, since: datetime, limit: int = 100) -> list[dict]:
        return [
            {"type": "test_event", "id": "evt_001", "timestamp": datetime.now(tz=UTC).isoformat()},
        ]

    async def subscribe(self, callback: Any) -> str:
        return "sub_001"

    async def unsubscribe(self, subscription_id: str) -> None:
        pass

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(
            status=ConnectorStatus.CONNECTED if self._healthy else ConnectorStatus.ERROR,
            last_checked_at=datetime.now(tz=UTC),
            error_message=None if self._healthy else "Connection failed",
            latency_ms=15,
        )

    async def send_verdict(self, evaluation_result: dict) -> bool:
        self._events_sent.append({"type": "verdict", **evaluation_result})
        return True

    async def send_alert(self, alert: dict) -> bool:
        self._events_sent.append({"type": "alert", **alert})
        return True

    async def send_notification(self, notification: dict) -> bool:
        self._events_sent.append({"type": "notification", **notification})
        return True


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------


class TestConnectorDomain:
    def test_connector_status_values(self) -> None:
        assert ConnectorStatus.CONNECTED == "CONNECTED"
        assert ConnectorStatus.DISCONNECTED == "DISCONNECTED"
        assert ConnectorStatus.ERROR == "ERROR"
        assert ConnectorStatus.INITIALIZING == "INITIALIZING"

    def test_connector_health(self) -> None:
        health = ConnectorHealth(
            status=ConnectorStatus.CONNECTED,
            last_checked_at=datetime.now(tz=UTC),
            error_message=None,
            latency_ms=10,
        )
        assert health.status == ConnectorStatus.CONNECTED

    def test_connector_config(self) -> None:
        config = ConnectorConfig(
            connector_type="hris_smarthr",
            tenant_id="tenant_1",
            credentials_ref="vault:smarthr/api_key",
            settings={"base_url": "https://api.smarthr.jp"},
            enabled=True,
        )
        assert config.connector_type == "hris_smarthr"
        assert config.enabled is True


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestConnectorRegistry:
    def test_register_and_get(self) -> None:
        registry = ConnectorRegistry()
        connector = MockConnector()
        registry.register("tenant_1", "test_mock", connector)
        retrieved = registry.get("tenant_1", "test_mock")
        assert retrieved is not None

    def test_tenant_isolation(self) -> None:
        registry = ConnectorRegistry()
        registry.register("tenant_1", "test_mock", MockConnector())
        assert registry.get("tenant_2", "test_mock") is None

    def test_unregister(self) -> None:
        registry = ConnectorRegistry()
        registry.register("tenant_1", "test_mock", MockConnector())
        registry.unregister("tenant_1", "test_mock")
        assert registry.get("tenant_1", "test_mock") is None

    def test_list_for_tenant(self) -> None:
        registry = ConnectorRegistry()
        registry.register("tenant_1", "type_a", MockConnector())
        registry.register("tenant_1", "type_b", MockConnector())
        registry.register("tenant_2", "type_a", MockConnector())
        assert len(registry.list_for_tenant("tenant_1")) == 2

    @pytest.mark.asyncio
    async def test_health_check_all(self) -> None:
        registry = ConnectorRegistry()
        registry.register("tenant_1", "test_mock", MockConnector())
        health = await registry.health_check_all("tenant_1")
        assert "test_mock" in health
        assert health["test_mock"].status == ConnectorStatus.CONNECTED


# ---------------------------------------------------------------------------
# Protocol tests
# ---------------------------------------------------------------------------


class TestConnectorProtocols:
    @pytest.mark.asyncio
    async def test_poll_events(self) -> None:
        connector = MockConnector()
        events = await connector.poll_events(since=datetime.now(tz=UTC))
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_send_verdict(self) -> None:
        connector = MockConnector()
        result = await connector.send_verdict({"verdict": "ALLOW"})
        assert result is True
        assert len(connector._events_sent) == 1

    @pytest.mark.asyncio
    async def test_send_alert(self) -> None:
        connector = MockConnector()
        assert await connector.send_alert({"severity": "HIGH"}) is True

    @pytest.mark.asyncio
    async def test_health_unhealthy(self) -> None:
        connector = MockConnector()
        connector._healthy = False
        health = await connector.health_check()
        assert health.status == ConnectorStatus.ERROR
