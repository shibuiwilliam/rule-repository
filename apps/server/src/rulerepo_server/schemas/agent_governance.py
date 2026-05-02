"""Pydantic request/response schemas for the Agent Governance API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class AgentRegisterRequest(BaseModel):
    """Request body for registering an agent."""

    agent_id: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(default="custom")
    capabilities: list[str] = Field(default_factory=list)


class ExceptionRequest(BaseModel):
    """Request body for an agent exception request."""

    agent_id: str
    rule_id: str
    context: str = Field(..., min_length=1)
    proposed_exception: str = Field(..., min_length=1)
    evidence: dict[str, Any] = Field(default_factory=dict)


class NegotiationRequest(BaseModel):
    """Request body for challenging a verdict."""

    agent_id: str
    evaluation_id: str
    rule_id: str
    original_verdict: str
    counter_argument: str = Field(..., min_length=1)
    proposed_action: str = Field(default="proceed_with_justification")


class SessionCreateRequest(BaseModel):
    """Request body for creating a governance session."""

    agent_id: str
    context_ref: str = ""
    project_id: str | None = None


class SessionJoinRequest(BaseModel):
    """Request body for joining a governance session."""

    agent_id: str


class VerdictPublishRequest(BaseModel):
    """Request body for publishing a verdict to a session."""

    rule_id: str
    verdict: str
    agent_id: str


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class AgentProfileResponse(BaseModel):
    """Agent governance profile response."""

    agent_id: str
    display_name: str
    agent_type: str
    capabilities: list[str]
    trust_level: str
    compliance_rate_30d: float
    violation_patterns: dict[str, Any]
    strength_areas: list[str]
    weakness_areas: list[str]
    can_propose_rules: bool
    can_vote_on_proposals: bool
    max_auto_fix_severity: str
    mastered_rules_count: int = 0
    created_at: str
    updated_at: str


class AgentListResponse(BaseModel):
    """Paginated list of agent profiles."""

    items: list[AgentProfileResponse]
    total: int
    page: int
    page_size: int


class ExceptionResponse(BaseModel):
    """Exception request response."""

    id: str
    agent_id: str
    rule_id: str
    context: str
    proposed_exception: str
    evidence: dict[str, Any]
    status: str
    proposal_id: str | None = None
    created_at: str


class NegotiationResponse(BaseModel):
    """Verdict negotiation response."""

    id: str
    agent_id: str
    evaluation_id: str
    rule_id: str
    original_verdict: str
    counter_argument: str
    proposed_action: str
    resolution: str
    resolved_by: str | None = None
    created_at: str


class SessionResponse(BaseModel):
    """Governance session response."""

    id: str
    project_id: str | None = None
    context_ref: str
    agent_ids: list[str]
    shared_verdicts: dict[str, Any]
    active: bool
    created_at: str
    closed_at: str | None = None


class PersonalizedRulesResponse(BaseModel):
    """Response for personalized rule delivery."""

    agent_id: str
    trust_level: str
    rules_delivered: int
    rules_suppressed: int
    rules: list[dict[str, Any]]
