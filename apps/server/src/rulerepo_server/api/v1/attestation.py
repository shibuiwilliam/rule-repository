"""REST API routes for attestation campaigns and responses.

See IMPROVEMENT.md RR-014.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.attestation import CampaignStatus, ResponseStatus
from rulerepo_server.services.attestation.service import AttestationService

logger = get_logger(__name__)

router = APIRouter(prefix="/attestation", tags=["attestation"])

# ---------------------------------------------------------------------------
# Singleton service (in-memory for now; will be replaced by DI with Postgres)
# ---------------------------------------------------------------------------

_service: AttestationService | None = None


def _get_service() -> AttestationService:
    """Return the module-level AttestationService singleton."""
    global _service
    if _service is None:
        _service = AttestationService()
    return _service


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateCampaignRequest(BaseModel):
    """Request body for creating an attestation campaign."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    rule_ids: list[str] = Field(..., min_length=1)
    target_users: list[str] = Field(default_factory=list)
    target_departments: list[str] = Field(default_factory=list)
    due_date: datetime | None = None
    reminder_interval_days: int = Field(default=7, ge=1, le=365)


class CampaignResponse(BaseModel):
    """Serialized attestation campaign."""

    id: str
    tenant_id: str
    title: str
    description: str
    rule_ids: list[str]
    target_users: list[str]
    target_departments: list[str]
    status: CampaignStatus
    due_date: datetime | None
    reminder_interval_days: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class CampaignProgressResponse(BaseModel):
    """Campaign completion statistics."""

    campaign_id: str
    total_users: int
    attested: int
    declined: int
    pending: int
    expired: int
    completion_rate: float


class RecordResponseRequest(BaseModel):
    """Request body for recording an attestation response."""

    user_id: str = Field(..., min_length=1)
    status: ResponseStatus = Field(
        ...,
        description="Must be ATTESTED or DECLINED.",
    )
    declined_reason: str = Field(default="", max_length=2000)


class AttestationResponseSchema(BaseModel):
    """Serialized attestation response."""

    id: str
    campaign_id: str
    user_id: str
    status: ResponseStatus
    attested_at: datetime | None
    declined_reason: str
    ip_address: str
    user_agent: str
    created_at: datetime


class PendingAttestationItem(BaseModel):
    """A single pending attestation for a user."""

    campaign_id: str
    campaign_title: str
    due_date: str | None
    rule_ids: list[str]
    response_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CreateCampaignRequest,
    tenant_id: str = Query(default="default"),
    svc: AttestationService = Depends(_get_service),
) -> CampaignResponse:
    """Create a new attestation campaign."""
    campaign = await svc.create_campaign(
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        rule_ids=body.rule_ids,
        target_users=body.target_users,
        target_departments=body.target_departments,
        due_date=body.due_date,
        reminder_interval_days=body.reminder_interval_days,
    )
    return CampaignResponse(
        id=str(campaign.id),
        tenant_id=campaign.tenant_id,
        title=campaign.title,
        description=campaign.description,
        rule_ids=campaign.rule_ids,
        target_users=campaign.target_users,
        target_departments=campaign.target_departments,
        status=campaign.status,
        due_date=campaign.due_date,
        reminder_interval_days=campaign.reminder_interval_days,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant_id: str = Query(default="default"),
    svc: AttestationService = Depends(_get_service),
) -> list[CampaignResponse]:
    """List all attestation campaigns for a tenant."""
    campaigns = await svc.list_campaigns(tenant_id=tenant_id)
    return [
        CampaignResponse(
            id=str(c.id),
            tenant_id=c.tenant_id,
            title=c.title,
            description=c.description,
            rule_ids=c.rule_ids,
            target_users=c.target_users,
            target_departments=c.target_departments,
            status=c.status,
            due_date=c.due_date,
            reminder_interval_days=c.reminder_interval_days,
            created_by=c.created_by,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in campaigns
    ]


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    svc: AttestationService = Depends(_get_service),
) -> CampaignResponse:
    """Get details of a single attestation campaign."""
    try:
        campaign = await svc.get_campaign(campaign_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return CampaignResponse(
        id=str(campaign.id),
        tenant_id=campaign.tenant_id,
        title=campaign.title,
        description=campaign.description,
        rule_ids=campaign.rule_ids,
        target_users=campaign.target_users,
        target_departments=campaign.target_departments,
        status=campaign.status,
        due_date=campaign.due_date,
        reminder_interval_days=campaign.reminder_interval_days,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/campaigns/{campaign_id}/progress", response_model=CampaignProgressResponse)
async def get_campaign_progress(
    campaign_id: UUID,
    svc: AttestationService = Depends(_get_service),
) -> CampaignProgressResponse:
    """Get completion statistics for an attestation campaign."""
    try:
        progress = await svc.get_campaign_progress(campaign_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return CampaignProgressResponse(
        campaign_id=str(progress.campaign_id),
        total_users=progress.total_users,
        attested=progress.attested,
        declined=progress.declined,
        pending=progress.pending,
        expired=progress.expired,
        completion_rate=progress.completion_rate,
    )


@router.post(
    "/campaigns/{campaign_id}/respond",
    response_model=AttestationResponseSchema,
    status_code=201,
)
async def record_response(
    campaign_id: UUID,
    body: RecordResponseRequest,
    request: Request,
    svc: AttestationService = Depends(_get_service),
) -> AttestationResponseSchema:
    """Record a user's attestation response for a campaign."""
    if body.status not in (ResponseStatus.ATTESTED, ResponseStatus.DECLINED):
        raise HTTPException(
            status_code=400,
            detail="Response status must be ATTESTED or DECLINED.",
        )

    try:
        response = await svc.record_response(
            campaign_id=campaign_id,
            user_id=body.user_id,
            status=body.status,
            declined_reason=body.declined_reason,
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return AttestationResponseSchema(
        id=str(response.id),
        campaign_id=str(response.campaign_id),
        user_id=response.user_id,
        status=response.status,
        attested_at=response.attested_at,
        declined_reason=response.declined_reason,
        ip_address=response.ip_address,
        user_agent=response.user_agent,
        created_at=response.created_at,
    )


@router.get("/pending", response_model=list[PendingAttestationItem])
async def get_pending_attestations(
    user_id: str = Query(..., description="User ID to look up pending attestations for."),
    tenant_id: str = Query(default="default"),
    svc: AttestationService = Depends(_get_service),
) -> list[PendingAttestationItem]:
    """Get all pending attestations for a specific user."""
    items = await svc.get_user_pending(user_id=user_id, tenant_id=tenant_id)
    return [PendingAttestationItem(**item) for item in items]


@router.post("/campaigns/{campaign_id}/close", response_model=CampaignResponse)
async def close_campaign(
    campaign_id: UUID,
    svc: AttestationService = Depends(_get_service),
) -> CampaignResponse:
    """Close a campaign and expire remaining pending responses."""
    try:
        campaign = await svc.close_campaign(campaign_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return CampaignResponse(
        id=str(campaign.id),
        tenant_id=campaign.tenant_id,
        title=campaign.title,
        description=campaign.description,
        rule_ids=campaign.rule_ids,
        target_users=campaign.target_users,
        target_departments=campaign.target_departments,
        status=campaign.status,
        due_date=campaign.due_date,
        reminder_interval_days=campaign.reminder_interval_days,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )
