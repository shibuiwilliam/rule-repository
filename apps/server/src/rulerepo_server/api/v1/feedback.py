"""REST API routes for the correction feedback loop."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import _get_optional_gemini
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.feedback import (
    CorrectionListResponse,
    CorrectionRequest,
    CorrectionResponse,
    FeedbackStatsResponse,
)
from rulerepo_server.services.feedback.service import FeedbackService

logger = get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _get_feedback_service(
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackService:
    """Build a FeedbackService with database session and optional Gemini client.

    Args:
        session: Async database session from dependency injection.

    Returns:
        Configured FeedbackService instance.
    """
    return FeedbackService(session, _get_optional_gemini())


@router.post("/corrections", response_model=CorrectionResponse)
async def submit_correction(
    body: CorrectionRequest,
    project_id: str | None = Query(default=None),
    svc: FeedbackService = Depends(_get_feedback_service),
) -> CorrectionResponse:
    """Submit a correction for analysis.

    Compares the original agent diff with the human-corrected diff,
    extracts a semantic delta, and runs analysis to classify the correction.
    """
    result = await svc.submit_correction(
        original_diff=body.original_diff,
        corrected_diff=body.corrected_diff,
        file_paths=body.file_paths,
        repository=body.repository,
        pr_number=body.pr_number,
        evaluation_ids=body.evaluation_ids,
        project_id=project_id,
    )
    return CorrectionResponse(**result)


@router.get("/corrections", response_model=CorrectionListResponse)
async def list_corrections(
    status: str | None = Query(default=None, description="Filter by status."),
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    project_id: str | None = Query(default=None),
    svc: FeedbackService = Depends(_get_feedback_service),
) -> CorrectionListResponse:
    """List corrections with optional status filter and pagination."""
    result = await svc.get_corrections(status=status, page=page, page_size=page_size, project_id=project_id)
    return CorrectionListResponse(
        items=[CorrectionResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/corrections/{correction_id}/approve")
async def approve_correction(
    correction_id: str,
    svc: FeedbackService = Depends(_get_feedback_service),
) -> dict[str, str | None]:
    """Approve a correction, optionally creating a new rule from it."""
    try:
        return await svc.approve_correction(correction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/corrections/{correction_id}/dismiss")
async def dismiss_correction(
    correction_id: str,
    svc: FeedbackService = Depends(_get_feedback_service),
) -> dict[str, str]:
    """Dismiss a correction without taking action."""
    try:
        return await svc.dismiss_correction(correction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    svc: FeedbackService = Depends(_get_feedback_service),
) -> FeedbackStatsResponse:
    """Return aggregate statistics about the correction feedback loop."""
    result = await svc.get_stats()
    return FeedbackStatsResponse(**result)
