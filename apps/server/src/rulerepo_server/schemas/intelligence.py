"""Pydantic schemas for the Intelligence & Analytics API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthScore(BaseModel):
    """Per-rule health score with dimension breakdown."""

    rule_id: str
    overall_score: float = Field(..., ge=0, le=100)
    completeness: float = Field(..., ge=0, le=100)
    clarity: float = Field(..., ge=0, le=100)
    test_coverage: float = Field(..., ge=0, le=100)
    freshness: float = Field(..., ge=0, le=100)
    activity: float = Field(..., ge=0, le=100)
    owner_engagement: float = Field(..., ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    computed_at: datetime | None = None


class RuleAnalytics(BaseModel):
    """Per-rule evaluation analytics."""

    rule_id: str
    period: str = "30d"
    total_evaluations: int = 0
    evaluations_per_day: float = 0.0
    allow_rate: float = 0.0
    deny_rate: float = 0.0
    needs_confirmation_rate: float = 0.0
    avg_latency_ms: float = 0.0
    top_scopes: list[str] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    """Corpus-wide intelligence dashboard data."""

    total_rules: int = 0
    avg_health_score: float = 0.0
    total_evaluations_30d: int = 0
    verdict_distribution: dict[str, int] = Field(default_factory=dict)
    active_drift_alerts: int = 0
    open_recommendations: int = 0
    health_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Buckets: excellent (80+), good (60-79), fair (40-59), poor (<40)",
    )


class Recommendation(BaseModel):
    """An automated improvement suggestion for a rule."""

    id: str
    rule_id: str
    type: str
    title: str
    description: str
    suggested_change: str | None = None
    related_rule_ids: list[str] = Field(default_factory=list)
    priority: str
    status: str = "open"
    created_at: datetime | None = None


class DriftAlert(BaseModel):
    """An alert about verdict instability on a rule."""

    id: str
    rule_id: str
    alert_type: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    severity: str
    status: str = "active"
    created_at: datetime | None = None


class ImpactSimulationRequest(BaseModel):
    """Request to simulate a rule change against historical evaluations."""

    rule_id: str
    proposed_statement: str = Field(..., min_length=1, max_length=10000)
    max_replays: int = Field(default=100, ge=1, le=500)


class ImpactSimulationResult(BaseModel):
    """Result of replaying historical evaluations with a modified rule."""

    rule_id: str
    proposed_statement: str
    total_replayed: int = 0
    verdicts_changed: int = 0
    allow_to_deny: int = 0
    deny_to_allow: int = 0
    affected_scopes: list[str] = Field(default_factory=list)
    risk_assessment: str = ""
