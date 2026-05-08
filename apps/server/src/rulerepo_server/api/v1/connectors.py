"""REST API routes for the Connector Hub.

Provides management endpoints for configuring, inspecting, and testing
bidirectional connectors to external business systems (HRIS, CRM, ERP,
etc.).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from rulerepo_server.services.connectors.base import (
    ConnectorConfig,
    ConnectorHealth,
    ConnectorStatus,
)
from rulerepo_server.services.connectors.registry import ConnectorRegistry
from rulerepo_server.services.connectors.service import ConnectorService

router = APIRouter(prefix="/connectors", tags=["connectors"])

# ---------------------------------------------------------------------------
# Singleton registry and service — in production, wire via DI container.
# ---------------------------------------------------------------------------
_registry = ConnectorRegistry()
_service = ConnectorService(_registry)


def _get_connector_service() -> ConnectorService:
    """Dependency provider for the ConnectorService."""
    return _service


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ConnectorConfigRequest(BaseModel):
    """Request body for configuring a new connector."""

    connector_type: str = Field(..., description="Machine-readable connector type identifier.")
    credentials_ref: str = Field(
        ...,
        description="Reference to a secrets-manager entry holding credentials.",
    )
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Connector-specific key-value settings.",
    )
    enabled: bool = Field(default=True, description="Whether the connector is active.")


class ConnectorConfigResponse(BaseModel):
    """Response body representing a connector configuration."""

    connector_type: str
    tenant_id: str
    credentials_ref: str
    settings: dict[str, Any]
    enabled: bool


class ConnectorHealthResponse(BaseModel):
    """Response body representing a connector health snapshot."""

    status: ConnectorStatus
    last_checked_at: str
    error_message: str | None = None
    latency_ms: float | None = None


class ConnectorListResponse(BaseModel):
    """Response body for listing configured connectors."""

    connectors: list[ConnectorConfigResponse]
    total: int


class AvailableConnectorType(BaseModel):
    """Metadata for a registered connector type."""

    connector_type: str
    description: str


class AvailableConnectorTypesResponse(BaseModel):
    """Response body for listing available connector types."""

    types: list[AvailableConnectorType]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Default tenant for local development.  In production, extract from
# the authenticated user's context.
_DEFAULT_TENANT = "default"


def _config_to_response(cfg: ConnectorConfig) -> dict[str, Any]:
    """Convert a ConnectorConfig to a response dict."""
    return {
        "connector_type": cfg.connector_type,
        "tenant_id": cfg.tenant_id,
        "credentials_ref": cfg.credentials_ref,
        "settings": cfg.settings,
        "enabled": cfg.enabled,
    }


def _health_to_response(health: ConnectorHealth) -> dict[str, Any]:
    """Convert a ConnectorHealth to a response dict."""
    return {
        "status": health.status.value,
        "last_checked_at": health.last_checked_at.isoformat(),
        "error_message": health.error_message,
        "latency_ms": health.latency_ms,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ConnectorListResponse)
async def list_connectors(
    service: ConnectorService = Depends(_get_connector_service),
) -> dict[str, Any]:
    """List all configured connectors for the current tenant."""
    configs = await service.list_connectors(_DEFAULT_TENANT)
    items = [_config_to_response(c) for c in configs]
    return {"connectors": items, "total": len(items)}


@router.post("", response_model=ConnectorConfigResponse, status_code=201)
async def configure_connector(
    body: ConnectorConfigRequest,
    service: ConnectorService = Depends(_get_connector_service),
) -> dict[str, Any]:
    """Configure and activate a new connector for the current tenant."""
    config = ConnectorConfig(
        connector_type=body.connector_type,
        tenant_id=_DEFAULT_TENANT,
        credentials_ref=body.credentials_ref,
        settings=body.settings,
        enabled=body.enabled,
    )
    result = await service.configure_connector(_DEFAULT_TENANT, config)
    return _config_to_response(result)


@router.delete("/{connector_type}", status_code=204)
async def remove_connector(
    connector_type: str,
    service: ConnectorService = Depends(_get_connector_service),
) -> None:
    """Deactivate and remove a connector for the current tenant."""
    await service.remove_connector(_DEFAULT_TENANT, connector_type)


@router.get(
    "/{connector_type}/health",
    response_model=ConnectorHealthResponse,
)
async def connector_health(
    connector_type: str,
    service: ConnectorService = Depends(_get_connector_service),
) -> dict[str, Any]:
    """Run a health check on a specific connector."""
    health = await service.get_connector_status(_DEFAULT_TENANT, connector_type)
    return _health_to_response(health)


@router.post(
    "/{connector_type}/test",
    response_model=ConnectorHealthResponse,
)
async def test_connection(
    connector_type: str,
    service: ConnectorService = Depends(_get_connector_service),
) -> dict[str, Any]:
    """Test connectivity for a connector without altering its state."""
    health = await service.test_connection(_DEFAULT_TENANT, connector_type)
    return _health_to_response(health)


@router.get("/available", response_model=AvailableConnectorTypesResponse)
async def list_available_types(
    service: ConnectorService = Depends(_get_connector_service),
) -> dict[str, Any]:
    """List all available (registered) connector types."""
    types = await service.list_available_types()
    return {"types": types, "total": len(types)}
