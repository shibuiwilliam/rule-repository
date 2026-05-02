"""API router for governance proposals — collaborative rule change workflow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import _get_optional_gemini
from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.proposal import (
    CommentCreate,
    CommentResponse,
    NotificationListResponse,
    NotificationResponse,
    ProposalCreate,
    ProposalListResponse,
    ProposalResponse,
    ProposalUpdate,
    VoteRequest,
)
from rulerepo_server.services.proposals.service import ProposalService

logger = get_logger(__name__)

router = APIRouter(prefix="/proposals", tags=["proposals"])


def _get_proposal_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProposalService:
    """Build a ProposalService with database session and optional Gemini client."""
    return ProposalService(session, _get_optional_gemini())


# ---------------------------------------------------------------------------
# Proposal CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=ProposalResponse, status_code=201)
async def create_proposal(
    body: ProposalCreate,
    project_id: str | None = Query(default=None),
    author_id: str = Query(default="system", description="Author user ID."),
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Create a new governance proposal."""
    try:
        result = await svc.create_proposal(
            proposal_type=body.proposal_type,
            title=body.title,
            description=body.description,
            target_rule_ids=body.target_rule_ids,
            change_spec=body.change_spec,
            required_approvers=body.required_approvers,
            author_id=author_id,
            project_id=project_id,
        )
        return ProposalResponse(**result)
    except (ValidationError, NotFoundError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=ProposalListResponse)
async def list_proposals(
    status: str | None = Query(default=None, description="Filter by status."),
    proposal_type: str | None = Query(default=None, description="Filter by type."),
    author_id: str | None = Query(default=None, description="Filter by author."),
    project_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalListResponse:
    """List proposals with optional filters and pagination."""
    result = await svc.list_proposals(
        status=status,
        proposal_type=proposal_type,
        author_id=author_id,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return ProposalListResponse(
        items=[ProposalResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: str,
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Get a single proposal with comments."""
    try:
        result = await svc.get_proposal(proposal_id)
        return ProposalResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: str,
    body: ProposalUpdate,
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Update a draft proposal."""
    try:
        result = await svc.update_proposal(
            proposal_id=proposal_id,
            title=body.title,
            description=body.description,
            target_rule_ids=body.target_rule_ids,
            change_spec=body.change_spec,
            required_approvers=body.required_approvers,
        )
        return ProposalResponse(**result)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Status Transitions
# ---------------------------------------------------------------------------


@router.post("/{proposal_id}/submit", response_model=ProposalResponse)
async def submit_proposal(
    proposal_id: str,
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Submit a draft proposal for review."""
    try:
        result = await svc.submit_for_review(proposal_id)
        return ProposalResponse(**result)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{proposal_id}/vote", response_model=ProposalResponse)
async def vote_on_proposal(
    proposal_id: str,
    body: VoteRequest,
    voter_id: str = Query(default="system", description="Voter user ID."),
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Cast an approval vote on a proposal."""
    try:
        result = await svc.vote(
            proposal_id=proposal_id,
            user_id=voter_id,
            vote=body.vote,
            condition=body.condition,
        )
        return ProposalResponse(**result)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{proposal_id}/enact", response_model=ProposalResponse)
async def enact_proposal(
    proposal_id: str,
    actor: str = Query(default="system", description="Actor performing enactment."),
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Enact an approved proposal — apply rule changes."""
    try:
        result = await svc.enact(proposal_id, actor=actor)
        return ProposalResponse(**result)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{proposal_id}/revert", response_model=ProposalResponse)
async def revert_proposal(
    proposal_id: str,
    actor: str = Query(default="system"),
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Revert an enacted proposal."""
    try:
        result = await svc.revert(proposal_id, actor=actor)
        return ProposalResponse(**result)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{proposal_id}/close", response_model=ProposalResponse)
async def close_proposal(
    proposal_id: str,
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Close a proposal without enacting."""
    try:
        result = await svc.close(proposal_id)
        return ProposalResponse(**result)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.post("/{proposal_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    proposal_id: str,
    body: CommentCreate,
    author_id: str = Query(default="system"),
    svc: ProposalService = Depends(_get_proposal_service),
) -> CommentResponse:
    """Add a comment to a proposal."""
    try:
        result = await svc.add_comment(
            proposal_id=proposal_id,
            body=body.body,
            author_id=author_id,
            parent_comment_id=body.parent_comment_id,
            comment_type=body.comment_type,
            suggestion_spec=body.suggestion_spec,
        )
        return CommentResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.post("/{proposal_id}/comments/{comment_id}/resolve", response_model=CommentResponse)
async def resolve_comment(
    proposal_id: str,
    comment_id: str,
    svc: ProposalService = Depends(_get_proposal_service),
) -> CommentResponse:
    """Mark a suggestion comment as resolved."""
    try:
        result = await svc.resolve_comment(comment_id)
        return CommentResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


@router.post("/{proposal_id}/analyze", response_model=ProposalResponse)
async def refresh_analysis(
    proposal_id: str,
    svc: ProposalService = Depends(_get_proposal_service),
) -> ProposalResponse:
    """Re-run conflict analysis and impact preview."""
    try:
        result = await svc.refresh_analysis(proposal_id)
        return ProposalResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@router.get("/notifications/inbox", response_model=NotificationListResponse)
async def get_notifications(
    user_id: str = Query(..., description="User ID to get notifications for."),
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    svc: ProposalService = Depends(_get_proposal_service),
) -> NotificationListResponse:
    """Get notifications for a user."""
    result = await svc.get_notifications(
        user_id=user_id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    return NotificationListResponse(
        items=[NotificationResponse(**item) for item in result["items"]],
        total=result["total"],
        unread_count=result["unread_count"],
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    svc: ProposalService = Depends(_get_proposal_service),
) -> NotificationResponse:
    """Mark a notification as read."""
    try:
        result = await svc.mark_notification_read(notification_id)
        return NotificationResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user_id: str = Query(..., description="User ID."),
    svc: ProposalService = Depends(_get_proposal_service),
) -> dict[str, int]:
    """Mark all notifications as read for a user."""
    count = await svc.mark_all_read(user_id)
    return {"marked_read": count}
