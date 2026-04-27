"""REST API routes for cross-project rule federation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.federation import (
    AddRuleRequest,
    EffectiveRuleResponse,
    FederationCreate,
    FederationResponse,
)
from rulerepo_server.services.federation.service import FederationService

logger = get_logger(__name__)

router = APIRouter(prefix="/federations", tags=["federation"])


def _get_federation_service(
    session: AsyncSession = Depends(get_db_session),
) -> FederationService:
    """Build a FederationService with the injected database session.

    Args:
        session: Async database session from dependency injection.

    Returns:
        A configured FederationService instance.
    """
    return FederationService(session=session)


@router.post("", status_code=201, response_model=FederationResponse)
async def create_federation(
    data: FederationCreate,
    service: FederationService = Depends(_get_federation_service),
) -> FederationResponse:
    """Create a new federation node.

    Args:
        data: Federation creation payload.
        service: Injected federation service.

    Returns:
        The created federation node.
    """
    try:
        result = await service.create_federation(
            name=data.name,
            level=data.level,
            parent_id=data.parent_id,
            description=data.description,
            default_scope=data.default_scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FederationResponse(**result)


@router.get("", response_model=list[FederationResponse])
async def list_federations(
    service: FederationService = Depends(_get_federation_service),
) -> list[FederationResponse]:
    """List all federation nodes as a tree structure.

    Args:
        service: Injected federation service.

    Returns:
        List of root federation nodes with nested children.
    """
    results = await service.list_federations()
    return [FederationResponse(**r) for r in results]


@router.get("/{federation_id}", response_model=FederationResponse)
async def get_federation(
    federation_id: str,
    service: FederationService = Depends(_get_federation_service),
) -> dict:
    """Get a federation node with its children and direct rules.

    Args:
        federation_id: UUID of the federation node.
        service: Injected federation service.

    Returns:
        Federation details with children and rules.
    """
    try:
        return await service.get_federation(federation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{federation_id}/rules", status_code=201)
async def add_rule_to_federation(
    federation_id: str,
    data: AddRuleRequest,
    service: FederationService = Depends(_get_federation_service),
) -> dict:
    """Add a rule to a federation node.

    Args:
        federation_id: UUID of the federation node.
        data: Rule membership payload.
        service: Injected federation service.

    Returns:
        Dict confirming the membership creation.
    """
    try:
        return await service.add_rule(
            federation_id=federation_id,
            rule_id=data.rule_id,
            override_parent_rule_id=data.override_parent_rule_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{federation_id}/rules/{rule_id}")
async def remove_rule_from_federation(
    federation_id: str,
    rule_id: str,
    service: FederationService = Depends(_get_federation_service),
) -> dict:
    """Remove a rule from a federation node.

    Args:
        federation_id: UUID of the federation node.
        rule_id: UUID of the rule to remove.
        service: Injected federation service.

    Returns:
        Dict confirming the removal.
    """
    try:
        return await service.remove_rule(federation_id=federation_id, rule_id=rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{federation_id}/effective-rules", response_model=list[EffectiveRuleResponse])
async def get_effective_rules(
    federation_id: str,
    service: FederationService = Depends(_get_federation_service),
) -> list[EffectiveRuleResponse]:
    """Resolve the effective rule set for a federation node.

    Walks the ancestor chain and applies overrides to produce
    the final set of rules that apply at this level.

    Args:
        federation_id: UUID of the target federation node.
        service: Injected federation service.

    Returns:
        List of effective rules with source federation info.
    """
    results = await service.get_effective_rules(federation_id)
    return [EffectiveRuleResponse(**r) for r in results]


@router.get("/{federation_id}/diff/{other_id}")
async def diff_federations(
    federation_id: str,
    other_id: str,
    service: FederationService = Depends(_get_federation_service),
) -> dict:
    """Compare the effective rule sets of two federation nodes.

    Args:
        federation_id: UUID of the first federation node.
        other_id: UUID of the second federation node.
        service: Injected federation service.

    Returns:
        Dict with only_in_a, only_in_b, and common rule lists.
    """
    return await service.diff_federations(federation_id, other_id)
