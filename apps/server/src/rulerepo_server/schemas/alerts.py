"""Pydantic schemas for the Alerts API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Single alert response."""

    id: str
    alert_type: str
    severity: str
    title: str
    description: str | None = None
    rule_id: str | None = None
    status: str
    created_at: str
    resolved_at: str | None = None


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    items: list[AlertResponse] = Field(default_factory=list)
    total: int = 0
