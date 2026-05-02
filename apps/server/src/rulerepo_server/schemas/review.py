"""Pydantic schemas for the Activity Review feature — two-tier compliance checking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from rulerepo_server.schemas.evaluation import FileInput, RuleVerdictResponse


class ActivityReviewRequest(BaseModel):
    """Request for activity review against all rules."""

    diff: str | None = Field(default=None, description="Unified diff text")
    files: list[FileInput] | None = Field(default=None, description="File paths with optional content")
    facts: dict[str, Any] | None = Field(default=None, description="Free-form context key-value pairs")
    intent: str | None = Field(default=None, description="Description of the activity")
    scope: str | None = Field(default=None, description="Rule scope filter")
    repository: str | None = Field(default=None, description="Repository identifier")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    project_id: str | None = Field(default=None, description="Project filter")
    use_llm_triage: bool = Field(default=True, description="Use LLM to confirm heuristic relevance classification")
    relevance_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum score to classify as RELEVANT")


class RuleRelevanceItem(BaseModel):
    """A single rule's relevance assessment from Tier 1."""

    rule_id: str
    rule_statement: str
    modality: str
    severity: str
    relevance: str  # RELEVANT | POTENTIALLY_RELEVANT | NOT_RELEVANT
    relevance_score: float
    relevance_reason: str = ""


class RoughReviewResponse(BaseModel):
    """Response from Tier 1 rough compliance review."""

    review_id: str
    total_rules_scanned: int
    relevant_count: int
    potentially_relevant_count: int
    not_relevant_count: int
    rule_assessments: list[RuleRelevanceItem]
    llm_triage_used: bool
    latency_ms: int
    timestamp: datetime


class DetailedReviewRequest(BaseModel):
    """Request for Tier 2 detailed review."""

    diff: str | None = Field(default=None)
    files: list[FileInput] | None = Field(default=None)
    facts: dict[str, Any] | None = Field(default=None)
    intent: str | None = Field(default=None)
    scope: str | None = Field(default=None)
    repository: str | None = Field(default=None)
    agent_id: str | None = Field(default=None)
    project_id: str | None = Field(default=None)
    rule_ids: list[str] = Field(..., min_length=1, description="Rule IDs to evaluate")


class DetailedReviewResponse(BaseModel):
    """Response from Tier 2 detailed compliance review."""

    review_id: str
    overall_verdict: str
    rule_verdicts: list[RuleVerdictResponse]
    violations: list[RuleVerdictResponse]
    warnings: list[RuleVerdictResponse]
    rules_evaluated: int
    rules_passed: int
    rules_violated: int
    rules_uncertain: int
    fix_summary: str | None = None
    model_ids_used: list[str]
    total_latency_ms: int
    chunk_count: int
    timestamp: datetime


class CombinedReviewResponse(BaseModel):
    """Response from combined Tier 1 + Tier 2 review."""

    rough_review: RoughReviewResponse
    detailed_review: DetailedReviewResponse
