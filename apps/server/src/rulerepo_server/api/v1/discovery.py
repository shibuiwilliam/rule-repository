"""REST API routes for automatic rule discovery."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import _get_optional_gemini
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.discovery import (
    CandidateResponse,
    ScanRequest,
    ScanResponse,
)
from rulerepo_server.services.discovery.service import DiscoveryService

logger = get_logger(__name__)

router = APIRouter(prefix="/discover", tags=["discovery"])


def _get_discovery_service(
    session: AsyncSession = Depends(get_db_session),
) -> DiscoveryService:
    """Build a DiscoveryService with database session and optional Gemini client.

    Args:
        session: Async database session from dependency injection.

    Returns:
        A configured DiscoveryService instance.
    """
    return DiscoveryService(session=session, gemini=_get_optional_gemini())


@router.post("/scan", status_code=201)
async def start_scan(
    data: ScanRequest,
    service: DiscoveryService = Depends(_get_discovery_service),
) -> ScanResponse:
    """Start a discovery scan to find candidate rules in source files.

    Args:
        data: The scan request with sources and file contents.
        service: Injected discovery service.

    Returns:
        ScanResponse with the scan ID and initial status.
    """
    scan_id = await service.start_scan(
        sources=data.sources,
        file_contents=data.file_contents,
        repository=data.repository,
    )
    scan = await service.get_scan(scan_id)
    return ScanResponse(
        scan_id=scan["scan_id"],
        status=scan["status"],
        candidates_found=scan["candidates_found"],
    )


@router.get("/scan/{scan_id}")
async def get_scan(
    scan_id: str,
    service: DiscoveryService = Depends(_get_discovery_service),
) -> ScanResponse:
    """Retrieve the status and results of a discovery scan.

    Args:
        scan_id: UUID of the scan to retrieve.
        service: Injected discovery service.

    Returns:
        ScanResponse with current scan details.
    """
    try:
        scan = await service.get_scan(scan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ScanResponse(
        scan_id=scan["scan_id"],
        status=scan["status"],
        candidates_found=scan["candidates_found"],
    )


@router.get("/candidates")
async def get_candidates(
    scan_id: str = Query(..., description="UUID of the scan"),
    status: str | None = Query(default=None, description="Filter by candidate status"),
    service: DiscoveryService = Depends(_get_discovery_service),
) -> list[CandidateResponse]:
    """List discovery candidates for a scan.

    Args:
        scan_id: UUID of the scan whose candidates to list.
        status: Optional filter (pending, approved, dismissed).
        service: Injected discovery service.

    Returns:
        List of candidate responses.
    """
    candidates = await service.get_candidates(scan_id, status=status)
    return [CandidateResponse(**c) for c in candidates]


@router.post("/candidates/{candidate_id}/approve")
async def approve_candidate(
    candidate_id: str,
    service: DiscoveryService = Depends(_get_discovery_service),
) -> dict:
    """Approve a candidate and create a rule from it.

    Args:
        candidate_id: UUID of the candidate to approve.
        service: Injected discovery service.

    Returns:
        Dict with created rule info.
    """
    try:
        return await service.approve_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/dismiss")
async def dismiss_candidate(
    candidate_id: str,
    service: DiscoveryService = Depends(_get_discovery_service),
) -> dict:
    """Dismiss a candidate, marking it as not useful.

    Args:
        candidate_id: UUID of the candidate to dismiss.
        service: Injected discovery service.

    Returns:
        Dict confirming dismissal.
    """
    try:
        return await service.dismiss_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
