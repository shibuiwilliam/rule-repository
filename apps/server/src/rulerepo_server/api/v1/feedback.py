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


# ---------------------------------------------------------------------------
# Draft Rule Proposals (Correction-to-Rule Flywheel)
# ---------------------------------------------------------------------------


@router.get("/proposals")
async def list_proposals(
    status: str | None = Query(default="pending"),
    project_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List draft rule proposals from the correction flywheel."""
    from sqlalchemy import func, select

    from rulerepo_server.adapters.postgres.models import DraftRuleProposalModel

    query = select(DraftRuleProposalModel).order_by(DraftRuleProposalModel.created_at.desc())
    count_query = select(func.count()).select_from(DraftRuleProposalModel)

    if status:
        query = query.where(DraftRuleProposalModel.status == status)
        count_query = count_query.where(DraftRuleProposalModel.status == status)
    if project_id:
        query = query.where(DraftRuleProposalModel.project_id == project_id)
        count_query = count_query.where(DraftRuleProposalModel.project_id == project_id)

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    proposals = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return {
        "items": [
            {
                "id": str(p.id),
                "project_id": str(p.project_id),
                "statement": p.statement,
                "modality": p.modality,
                "severity": p.severity,
                "scope": p.scope,
                "rationale": p.rationale,
                "evidence_correction_ids": p.evidence_correction_ids,
                "cluster_size": p.cluster_size,
                "confidence": p.confidence,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in proposals
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Approve a draft proposal — create a rule with experimental maturity."""
    from uuid import UUID, uuid4

    from sqlalchemy import select

    from rulerepo_server.adapters.postgres.models import DraftRuleProposalModel, RuleModel

    result = await session.execute(select(DraftRuleProposalModel).where(DraftRuleProposalModel.id == UUID(proposal_id)))
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal already {proposal.status}")

    # Create rule with experimental maturity (shadow mode)
    rule_id = uuid4()
    rule = RuleModel(
        id=rule_id,
        project_id=proposal.project_id,
        maturity_level="experimental",
        statement=proposal.statement,
        modality=proposal.modality,
        severity=proposal.severity,
        status="APPROVED",
        scope=proposal.scope,
        rationale=proposal.rationale,
    )
    session.add(rule)

    proposal.status = "approved"
    proposal.created_rule_id = rule_id
    proposal.reviewed_at = __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc)

    await session.flush()

    logger.info(
        "proposal_approved",
        proposal_id=proposal_id,
        rule_id=str(rule_id),
    )

    return {
        "proposal_id": proposal_id,
        "rule_id": str(rule_id),
        "status": "approved",
        "maturity_level": "experimental",
    }


@router.post("/proposals/{proposal_id}/dismiss")
async def dismiss_proposal(
    proposal_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Dismiss a draft proposal."""
    from uuid import UUID

    from sqlalchemy import select

    from rulerepo_server.adapters.postgres.models import DraftRuleProposalModel

    result = await session.execute(select(DraftRuleProposalModel).where(DraftRuleProposalModel.id == UUID(proposal_id)))
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.status = "dismissed"
    proposal.reviewed_at = __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc)
    await session.flush()

    return {"proposal_id": proposal_id, "status": "dismissed"}
