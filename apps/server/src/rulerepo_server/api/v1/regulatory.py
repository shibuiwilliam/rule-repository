"""Regulatory source feed API endpoints (RR-012).

Manages external regulatory sources (laws, regulations, standards)
and tracks amendments that affect downstream rules.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.regulatory.service import RegulatoryService

logger = get_logger(__name__)
router = APIRouter(prefix="/regulatory", tags=["regulatory"])

# Singleton service
_service = RegulatoryService()


# --- Schemas ---


class SourceCreate(BaseModel):
    """Request to register a regulatory source."""

    jurisdiction: str = Field(..., description="Country/region code")
    authority: str = Field(..., description="Issuing authority")
    citation: str = Field(..., description="Official citation")
    title: str = Field(..., description="Human-readable title")
    source_type: str = Field(default="law")
    effective_date: str | None = None
    source_url: str = ""
    feed_id: str = ""


class SourceResponse(BaseModel):
    """Regulatory source response."""

    id: str
    jurisdiction: str
    authority: str
    citation: str
    title: str
    source_type: str
    effective_date: str | None
    source_url: str
    feed_id: str


class AmendmentCreate(BaseModel):
    """Request to record an amendment."""

    summary: str = Field(..., min_length=1)
    amendment_date: str | None = None
    diff_url: str = ""


class AmendmentResponse(BaseModel):
    """Amendment response."""

    id: str
    source_id: str
    summary: str
    amendment_date: str | None
    status: str
    affected_rule_count: int


class LinkRuleRequest(BaseModel):
    """Request to link a rule to a source."""

    rule_id: str


# --- Endpoints ---


@router.post("/sources", status_code=201)
async def create_source(req: SourceCreate) -> SourceResponse:
    """Register a new regulatory source."""
    source = await _service.create_source(
        jurisdiction=req.jurisdiction,
        authority=req.authority,
        citation=req.citation,
        title=req.title,
        source_type=req.source_type,
        effective_date=req.effective_date,
        source_url=req.source_url,
        feed_id=req.feed_id,
    )
    return SourceResponse(
        id=str(source.id),
        jurisdiction=source.jurisdiction,
        authority=source.authority,
        citation=source.citation,
        title=source.title,
        source_type=source.source_type.value,
        effective_date=(source.effective_date.isoformat() if source.effective_date else None),
        source_url=source.source_url,
        feed_id=source.feed_id,
    )


@router.get("/sources")
async def list_sources(
    jurisdiction: str | None = None,
    source_type: str | None = None,
) -> list[SourceResponse]:
    """List regulatory sources."""
    sources = await _service.list_sources(
        jurisdiction=jurisdiction,
        source_type=source_type,
    )
    return [
        SourceResponse(
            id=str(s.id),
            jurisdiction=s.jurisdiction,
            authority=s.authority,
            citation=s.citation,
            title=s.title,
            source_type=s.source_type.value,
            effective_date=(s.effective_date.isoformat() if s.effective_date else None),
            source_url=s.source_url,
            feed_id=s.feed_id,
        )
        for s in sources
    ]


@router.get("/sources/{source_id}")
async def get_source(source_id: UUID) -> SourceResponse:
    """Get a regulatory source by ID."""
    s = await _service.get_source(source_id)
    return SourceResponse(
        id=str(s.id),
        jurisdiction=s.jurisdiction,
        authority=s.authority,
        citation=s.citation,
        title=s.title,
        source_type=s.source_type.value,
        effective_date=(s.effective_date.isoformat() if s.effective_date else None),
        source_url=s.source_url,
        feed_id=s.feed_id,
    )


@router.post("/sources/{source_id}/rules", status_code=201)
async def link_rule(source_id: UUID, req: LinkRuleRequest) -> dict:
    """Link a rule to a regulatory source (DERIVES_FROM)."""
    await _service.link_rule(source_id, UUID(req.rule_id))
    return {"status": "linked", "source_id": str(source_id), "rule_id": req.rule_id}


@router.get("/sources/{source_id}/rules")
async def get_derived_rules(source_id: UUID) -> dict:
    """Get rules that derive from this regulatory source."""
    rule_ids = await _service.get_derived_rules(source_id)
    return {"source_id": str(source_id), "rule_ids": rule_ids, "count": len(rule_ids)}


@router.post("/sources/{source_id}/amendments", status_code=201)
async def record_amendment(source_id: UUID, req: AmendmentCreate) -> AmendmentResponse:
    """Record an amendment to a regulatory source."""
    amendment = await _service.record_amendment(
        source_id=source_id,
        summary=req.summary,
        amendment_date=req.amendment_date,
        diff_url=req.diff_url,
    )
    return AmendmentResponse(
        id=str(amendment.id),
        source_id=str(amendment.source_id),
        summary=amendment.summary,
        amendment_date=(amendment.amendment_date.isoformat() if amendment.amendment_date else None),
        status=amendment.status.value,
        affected_rule_count=len(amendment.affected_rule_ids),
    )


@router.post("/amendments/{amendment_id}/propagate")
async def propagate_amendment(amendment_id: UUID) -> dict:
    """Propagate an amendment — mark affected rules as needs_review."""
    return await _service.propagate_amendment(amendment_id)


@router.get("/amendments")
async def list_amendments(
    source_id: UUID | None = None,
    status: str | None = None,
) -> list[AmendmentResponse]:
    """List amendments with optional filters."""
    amendments = await _service.list_amendments(
        source_id=source_id,
        status=status,
    )
    return [
        AmendmentResponse(
            id=str(a.id),
            source_id=str(a.source_id),
            summary=a.summary,
            amendment_date=(a.amendment_date.isoformat() if a.amendment_date else None),
            status=a.status.value,
            affected_rule_count=len(a.affected_rule_ids),
        )
        for a in amendments
    ]
