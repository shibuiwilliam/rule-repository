"""Pydantic schemas for the Snapshots & Deployments API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SnapshotCreate(BaseModel):
    """Request body to create a new rule-set snapshot."""

    name: str = Field(..., min_length=1, max_length=255)
    scope_filter: list[str] = Field(default_factory=list)
    description: str | None = None
    created_by: str = "system"


class SnapshotResponse(BaseModel):
    """Response representing a rule-set snapshot."""

    id: str
    name: str
    description: str | None = None
    scope_filter: list[str] = Field(default_factory=list)
    rule_count: int
    created_by: str
    created_at: str


class DeployRequest(BaseModel):
    """Request body to deploy a snapshot to an environment."""

    environment: str = Field(..., min_length=1, max_length=50)
    deployed_by: str = "system"


class DeploymentResponse(BaseModel):
    """Response representing a snapshot deployment."""

    id: str
    snapshot_id: str
    environment: str
    active: bool
    deployed_by: str
    deployed_at: str
    rolled_back_at: str | None = None


class SimulateRequest(BaseModel):
    """Request body to run an impact simulation."""

    compare_to: str = "production"
    sample_size: int = Field(default=100, ge=1, le=1000)


class SimulateResponse(BaseModel):
    """Response from an impact simulation."""

    total_replayed: int
    rules_added: int
    rules_removed: int
    risk_assessment: str
