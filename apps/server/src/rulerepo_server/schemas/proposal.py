"""Pydantic request/response schemas for the Proposals API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ProposalCreate(BaseModel):
    """Request body for creating a new proposal."""

    proposal_type: str = Field(..., description="Type: create, amend, retire, merge, split, override.")
    title: str = Field(..., min_length=1, max_length=500, description="Short title for the proposal.")
    description: str = Field(default="", description="Detailed description (Markdown).")
    target_rule_ids: list[str] = Field(default_factory=list, description="IDs of rules being changed.")
    change_spec: dict[str, Any] = Field(default_factory=dict, description="Structured diff of proposed changes.")
    required_approvers: list[str] = Field(default_factory=list, description="User IDs who must approve.")


class ProposalUpdate(BaseModel):
    """Request body for updating a draft proposal."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    target_rule_ids: list[str] | None = None
    change_spec: dict[str, Any] | None = None
    required_approvers: list[str] | None = None


class VoteRequest(BaseModel):
    """Request body for casting a vote on a proposal."""

    vote: str = Field(..., description="Vote: approve, reject, or conditional.")
    condition: str | None = Field(default=None, description="Condition for conditional approval.")


class CommentCreate(BaseModel):
    """Request body for adding a comment to a proposal."""

    body: str = Field(..., min_length=1, description="Comment text (Markdown).")
    parent_comment_id: str | None = Field(default=None, description="Parent comment ID for threading.")
    comment_type: str = Field(default="comment", description="Type: comment, suggestion, or resolution.")
    suggestion_spec: dict[str, Any] | None = Field(
        default=None, description="For suggestions: {field, original, proposed}."
    )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class CommentResponse(BaseModel):
    """Response for a single proposal comment."""

    id: str
    proposal_id: str
    parent_comment_id: str | None = None
    author_id: str
    body: str
    comment_type: str
    suggestion_spec: dict[str, Any] | None = None
    resolved: bool = False
    created_at: str


class ProposalResponse(BaseModel):
    """Full proposal representation returned by the API."""

    id: str
    project_id: str | None = None
    proposal_type: str
    status: str
    author_id: str
    title: str
    description: str
    change_spec: dict[str, Any]
    target_rule_ids: list[str]
    conflict_analysis: dict[str, Any] | None = None
    impact_preview: dict[str, Any] | None = None
    required_approvers: list[str]
    approval_votes: list[dict[str, Any]]
    comments: list[CommentResponse] = Field(default_factory=list)
    enacted_at: str | None = None
    created_at: str
    updated_at: str


class ProposalListResponse(BaseModel):
    """Paginated list of proposals."""

    items: list[ProposalResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    """Response for a single notification."""

    id: str
    user_id: str
    proposal_id: str | None = None
    notification_type: str
    title: str
    body: str
    read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    items: list[NotificationResponse]
    total: int
    unread_count: int
