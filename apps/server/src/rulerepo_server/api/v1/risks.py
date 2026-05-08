"""REST API routes for the Risk Register.

See IMPROVEMENT.md RR-019.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.risk import RiskImpact, RiskLikelihood, RiskStatus
from rulerepo_server.services.risk.service import RiskService

logger = get_logger(__name__)

router = APIRouter(prefix="/risks", tags=["risks"])

# ---------------------------------------------------------------------------
# Singleton service (in-memory for now; will be replaced by DI with Postgres)
# ---------------------------------------------------------------------------

_service: RiskService | None = None


def _get_service() -> RiskService:
    """Return the module-level RiskService singleton."""
    global _service
    if _service is None:
        _service = RiskService()
    return _service


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateRiskRequest(BaseModel):
    """Request body for creating a risk."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    likelihood: RiskLikelihood = RiskLikelihood.POSSIBLE
    impact: RiskImpact = RiskImpact.MODERATE
    status: RiskStatus = RiskStatus.IDENTIFIED
    owner: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=200)
    framework_refs: list[str] = Field(default_factory=list)
    inherent_score: float = Field(default=0.0, ge=0.0)
    residual_score: float = Field(default=0.0, ge=0.0)


class UpdateRiskRequest(BaseModel):
    """Request body for updating a risk (all fields optional)."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    likelihood: RiskLikelihood | None = None
    impact: RiskImpact | None = None
    status: RiskStatus | None = None
    owner: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=200)
    framework_refs: list[str] | None = None
    inherent_score: float | None = Field(default=None, ge=0.0)
    residual_score: float | None = Field(default=None, ge=0.0)


class RiskResponse(BaseModel):
    """Serialized risk entity."""

    id: str
    tenant_id: str
    title: str
    description: str
    likelihood: RiskLikelihood
    impact: RiskImpact
    status: RiskStatus
    owner: str
    category: str
    framework_refs: list[str]
    inherent_score: float
    residual_score: float
    created_at: datetime
    updated_at: datetime


class MapRuleRequest(BaseModel):
    """Request body for mapping a rule to a risk."""

    rule_id: str = Field(..., description="UUID of the rule to map.")
    mitigation_strength: str = Field(
        default="partial",
        description="One of: full, partial, minimal.",
    )
    notes: str = Field(default="", max_length=2000)


class RiskRuleMappingResponse(BaseModel):
    """Serialized risk-rule mapping."""

    risk_id: str
    rule_id: str
    mitigation_strength: str
    notes: str
    created_at: datetime


class RiskCoverageResponse(BaseModel):
    """Coverage summary for a single risk."""

    risk_id: str
    risk_title: str
    total_rules: int
    full: int
    partial: int
    minimal: int
    coverage_pct: float
    rules: list[dict[str, str]]


class FrameworkCoverageRisk(BaseModel):
    """Per-risk entry in a framework coverage report."""

    risk_id: str
    risk_title: str
    status: str
    rule_count: int
    covered: bool


class FrameworkCoverageResponse(BaseModel):
    """Coverage summary for a regulatory framework."""

    framework_ref: str
    total_risks: int
    covered_risks: int
    uncovered_risks: int
    coverage_pct: float
    risks: list[FrameworkCoverageRisk]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _risk_to_response(risk: object) -> RiskResponse:
    """Convert a Risk domain object to a RiskResponse schema."""
    from rulerepo_server.domain.risk import Risk as RiskDomain

    r: RiskDomain = risk  # type: ignore[assignment]
    return RiskResponse(
        id=str(r.id),
        tenant_id=r.tenant_id,
        title=r.title,
        description=r.description,
        likelihood=r.likelihood,
        impact=r.impact,
        status=r.status,
        owner=r.owner,
        category=r.category,
        framework_refs=r.framework_refs,
        inherent_score=r.inherent_score,
        residual_score=r.residual_score,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=RiskResponse, status_code=201)
async def create_risk(
    body: CreateRiskRequest,
    tenant_id: str = Query(default="default"),
    svc: RiskService = Depends(_get_service),
) -> RiskResponse:
    """Create a new risk in the Risk Register."""
    risk = await svc.create_risk(
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        likelihood=body.likelihood,
        impact=body.impact,
        status=body.status,
        owner=body.owner,
        category=body.category,
        framework_refs=body.framework_refs,
        inherent_score=body.inherent_score,
        residual_score=body.residual_score,
    )
    return _risk_to_response(risk)


@router.get("", response_model=list[RiskResponse])
async def list_risks(
    tenant_id: str = Query(default="default"),
    category: str | None = Query(default=None),
    status: RiskStatus | None = Query(default=None),
    framework_ref: str | None = Query(default=None),
    svc: RiskService = Depends(_get_service),
) -> list[RiskResponse]:
    """List risks, optionally filtered by category, status, or framework."""
    risks = await svc.list_risks(
        tenant_id,
        category=category,
        status=status,
        framework_ref=framework_ref,
    )
    return [_risk_to_response(r) for r in risks]


@router.get("/frameworks/{framework_ref}/coverage", response_model=FrameworkCoverageResponse)
async def get_framework_coverage(
    framework_ref: str,
    tenant_id: str = Query(default="default"),
    svc: RiskService = Depends(_get_service),
) -> FrameworkCoverageResponse:
    """Get rule coverage summary for a regulatory framework."""
    result = await svc.get_framework_coverage(framework_ref, tenant_id)
    return FrameworkCoverageResponse(
        framework_ref=result["framework_ref"],  # type: ignore[arg-type]
        total_risks=result["total_risks"],  # type: ignore[arg-type]
        covered_risks=result["covered_risks"],  # type: ignore[arg-type]
        uncovered_risks=result["uncovered_risks"],  # type: ignore[arg-type]
        coverage_pct=result["coverage_pct"],  # type: ignore[arg-type]
        risks=[
            FrameworkCoverageRisk(**r)  # type: ignore[arg-type]
            for r in result["risks"]  # type: ignore[union-attr]
        ],
    )


@router.get("/{risk_id}", response_model=RiskResponse)
async def get_risk(
    risk_id: UUID,
    svc: RiskService = Depends(_get_service),
) -> RiskResponse:
    """Get details of a single risk."""
    try:
        risk = await svc.get_risk(risk_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return _risk_to_response(risk)


@router.put("/{risk_id}", response_model=RiskResponse)
async def update_risk(
    risk_id: UUID,
    body: UpdateRiskRequest,
    svc: RiskService = Depends(_get_service),
) -> RiskResponse:
    """Update an existing risk."""
    try:
        risk = await svc.update_risk(
            risk_id,
            title=body.title,
            description=body.description,
            likelihood=body.likelihood,
            impact=body.impact,
            status=body.status,
            owner=body.owner,
            category=body.category,
            framework_refs=body.framework_refs,
            inherent_score=body.inherent_score,
            residual_score=body.residual_score,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return _risk_to_response(risk)


@router.post("/{risk_id}/rules", response_model=RiskRuleMappingResponse, status_code=201)
async def map_rule_to_risk(
    risk_id: UUID,
    body: MapRuleRequest,
    svc: RiskService = Depends(_get_service),
) -> RiskRuleMappingResponse:
    """Map a rule (control) to a risk it mitigates."""
    try:
        mapping = await svc.map_rule_to_risk(
            risk_id=risk_id,
            rule_id=UUID(body.rule_id),
            mitigation_strength=body.mitigation_strength,
            notes=body.notes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return RiskRuleMappingResponse(
        risk_id=str(mapping.risk_id),
        rule_id=str(mapping.rule_id),
        mitigation_strength=mapping.mitigation_strength,
        notes=mapping.notes,
        created_at=mapping.created_at,
    )


@router.get("/{risk_id}/coverage", response_model=RiskCoverageResponse)
async def get_risk_coverage(
    risk_id: UUID,
    svc: RiskService = Depends(_get_service),
) -> RiskCoverageResponse:
    """Get rule coverage summary for a single risk."""
    try:
        result = await svc.get_risk_coverage(risk_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return RiskCoverageResponse(
        risk_id=result["risk_id"],  # type: ignore[arg-type]
        risk_title=result["risk_title"],  # type: ignore[arg-type]
        total_rules=result["total_rules"],  # type: ignore[arg-type]
        full=result["full"],  # type: ignore[arg-type]
        partial=result["partial"],  # type: ignore[arg-type]
        minimal=result["minimal"],  # type: ignore[arg-type]
        coverage_pct=result["coverage_pct"],  # type: ignore[arg-type]
        rules=result["rules"],  # type: ignore[arg-type]
    )
