"""Pydantic schemas for the Gateway API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NormalizedEvent(BaseModel):
    """A webhook event normalized into a standard structure."""

    source: str
    event_type: str
    actor: str | None = None
    subject: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class PolicyCreate(BaseModel):
    """Schema for creating an enforcement policy."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    event_source: str = Field(..., description="github, slack, generic")
    event_type_pattern: str = Field(..., description="e.g., pull_request.*, message.*")
    rule_scope: str | None = None
    rule_modality_filter: list[str] = Field(default_factory=list)
    rule_severity_min: str | None = None
    evaluation_mode: str = "preflight"
    context_extraction_prompt: str | None = None
    response_actions: list[dict[str, Any]] = Field(default_factory=list)
    on_deny: str = "notify"
    enabled: bool = True


class PolicyResponse(BaseModel):
    """Response for an enforcement policy."""

    id: str
    name: str
    description: str | None = None
    event_source: str
    event_type_pattern: str
    rule_scope: str | None = None
    evaluation_mode: str
    on_deny: str
    enabled: bool
    created_at: datetime | None = None


class GatewayEvaluationResponse(BaseModel):
    """Response for a gateway evaluation result."""

    id: str
    policy_id: str
    event_source: str
    event_type: str
    verdict: str
    violations: list[dict[str, Any]] | None = None
    actions_taken: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int | None = None
    created_at: datetime | None = None


class WebhookIngestRequest(BaseModel):
    """Generic webhook payload for ingestion."""

    event_type: str = Field(default="generic", description="Event type identifier")
    payload: dict[str, Any] = Field(default_factory=dict)
    callback_url: str | None = Field(default=None, description="URL to POST the verdict back to")
