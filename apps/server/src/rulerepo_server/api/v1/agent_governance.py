"""API router for autonomous agent governance."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.agent_governance import (
    AgentListResponse,
    AgentProfileResponse,
    AgentRegisterRequest,
    ExceptionRequest,
    ExceptionResponse,
    NegotiationRequest,
    NegotiationResponse,
    PersonalizedRulesResponse,
    SessionCreateRequest,
    SessionJoinRequest,
    SessionResponse,
    VerdictPublishRequest,
)
from rulerepo_server.services.agent_governance.service import AgentGovernanceService

logger = get_logger(__name__)

router = APIRouter(prefix="/agent-governance", tags=["agent-governance"])


def _get_service(session: AsyncSession = Depends(get_db_session)) -> AgentGovernanceService:
    return AgentGovernanceService(session)


# ---------------------------------------------------------------------------
# Agent Profile
# ---------------------------------------------------------------------------


@router.post("/register", response_model=AgentProfileResponse, status_code=201)
async def register_agent(
    body: AgentRegisterRequest,
    svc: AgentGovernanceService = Depends(_get_service),
) -> AgentProfileResponse:
    """Register a new agent or return existing profile."""
    try:
        result = await svc.register_agent(
            agent_id=body.agent_id,
            display_name=body.display_name,
            agent_type=body.agent_type,
            capabilities=body.capabilities,
        )
        return AgentProfileResponse(**result)
    except ValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    sort_by: str = Query(default="compliance_rate_30d"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: AgentGovernanceService = Depends(_get_service),
) -> AgentListResponse:
    """List agents as a compliance leaderboard."""
    result = await svc.list_agents(sort_by=sort_by, page=page, page_size=page_size)
    return AgentListResponse(
        items=[AgentProfileResponse(**p) for p in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/profile/{agent_id}", response_model=AgentProfileResponse)
async def get_agent_profile(
    agent_id: str,
    svc: AgentGovernanceService = Depends(_get_service),
) -> AgentProfileResponse:
    """Get an agent's governance profile."""
    try:
        result = await svc.get_profile(agent_id)
        return AgentProfileResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Adaptive Rule Delivery
# ---------------------------------------------------------------------------


@router.get("/rules/{agent_id}", response_model=PersonalizedRulesResponse)
async def get_personalized_rules(
    agent_id: str,
    max_rules: int = Query(default=20, ge=1, le=100),
    svc: AgentGovernanceService = Depends(_get_service),
) -> PersonalizedRulesResponse:
    """Get rules personalized to an agent's history and mastery."""
    try:
        result = await svc.get_personalized_rules(agent_id=agent_id, max_rules=max_rules)
        return PersonalizedRulesResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.get("/mastery/{agent_id}")
async def get_mastery_report(
    agent_id: str,
    svc: AgentGovernanceService = Depends(_get_service),
) -> dict:
    """Get an agent's rule mastery report."""
    try:
        return await svc.get_mastery_report(agent_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Exception Requests
# ---------------------------------------------------------------------------


@router.post("/exception-request", response_model=ExceptionResponse, status_code=201)
async def request_exception(
    body: ExceptionRequest,
    svc: AgentGovernanceService = Depends(_get_service),
) -> ExceptionResponse:
    """Submit a rule exception request."""
    try:
        result = await svc.request_exception(
            agent_id=body.agent_id,
            rule_id=body.rule_id,
            context=body.context,
            proposed_exception=body.proposed_exception,
            evidence=body.evidence,
        )
        return ExceptionResponse(**result)
    except (NotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/exceptions")
async def list_exceptions(
    agent_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: AgentGovernanceService = Depends(_get_service),
) -> dict:
    """List exception requests."""
    return await svc.list_exceptions(agent_id=agent_id, status=status, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Verdict Negotiations
# ---------------------------------------------------------------------------


@router.post("/negotiate", response_model=NegotiationResponse, status_code=201)
async def challenge_verdict(
    body: NegotiationRequest,
    svc: AgentGovernanceService = Depends(_get_service),
) -> NegotiationResponse:
    """Challenge a verdict with a counter-argument."""
    try:
        result = await svc.challenge_verdict(
            agent_id=body.agent_id,
            evaluation_id=body.evaluation_id,
            rule_id=body.rule_id,
            original_verdict=body.original_verdict,
            counter_argument=body.counter_argument,
            proposed_action=body.proposed_action,
        )
        return NegotiationResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.get("/negotiations")
async def list_negotiations(
    agent_id: str | None = Query(default=None),
    resolution: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: AgentGovernanceService = Depends(_get_service),
) -> dict:
    """List verdict negotiations."""
    return await svc.list_negotiations(agent_id=agent_id, resolution=resolution, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Governance Sessions
# ---------------------------------------------------------------------------


@router.post("/session", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreateRequest,
    svc: AgentGovernanceService = Depends(_get_service),
) -> SessionResponse:
    """Create a multi-agent governance session."""
    try:
        result = await svc.create_session(
            agent_id=body.agent_id,
            context_ref=body.context_ref,
            project_id=body.project_id,
        )
        return SessionResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.post("/session/{session_id}/join", response_model=SessionResponse)
async def join_session(
    session_id: str,
    body: SessionJoinRequest,
    svc: AgentGovernanceService = Depends(_get_service),
) -> SessionResponse:
    """Join an existing governance session."""
    try:
        result = await svc.join_session(session_id=session_id, agent_id=body.agent_id)
        return SessionResponse(**result)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    svc: AgentGovernanceService = Depends(_get_service),
) -> SessionResponse:
    """Get session details."""
    try:
        result = await svc.get_session(session_id)
        return SessionResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.post("/session/{session_id}/verdict", response_model=SessionResponse)
async def publish_verdict(
    session_id: str,
    body: VerdictPublishRequest,
    svc: AgentGovernanceService = Depends(_get_service),
) -> SessionResponse:
    """Publish a verdict to the shared session."""
    try:
        result = await svc.publish_verdict(
            session_id=session_id,
            rule_id=body.rule_id,
            verdict=body.verdict,
            agent_id=body.agent_id,
        )
        return SessionResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.post("/session/{session_id}/close", response_model=SessionResponse)
async def close_session(
    session_id: str,
    svc: AgentGovernanceService = Depends(_get_service),
) -> SessionResponse:
    """Close a governance session."""
    try:
        result = await svc.close_session(session_id)
        return SessionResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
