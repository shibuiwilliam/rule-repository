"""Pydantic request/response schemas for the correction feedback loop."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorrectionRequest(BaseModel):
    """Request body for submitting a correction."""

    original_diff: str = Field(..., description="The agent-generated diff.")
    corrected_diff: str = Field(..., description="The human-corrected diff.")
    file_paths: list[str] = Field(default_factory=list, description="Affected file paths.")
    repository: str | None = Field(default=None, description="Repository identifier.")
    pr_number: int | None = Field(default=None, description="Pull request number.")
    evaluation_ids: list[str] = Field(
        default_factory=list, description="IDs of related evaluations."
    )


class CorrectionResponse(BaseModel):
    """Response after submitting or retrieving a correction."""

    id: str
    analysis_type: str | None = None
    matched_rule_ids: list[str] = Field(default_factory=list)
    candidate_statement: str | None = None
    confidence: float | None = None
    status: str
    created_at: str


class CorrectionListResponse(BaseModel):
    """Paginated list of corrections."""

    items: list[CorrectionResponse]
    total: int
    page: int
    page_size: int


class FeedbackStatsResponse(BaseModel):
    """Aggregate statistics about the correction feedback loop."""

    total_corrections: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    rules_created: int
    top_violated_rules: list[dict[str, int | str]]
