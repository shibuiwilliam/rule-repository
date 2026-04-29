"""REST API routes for rule CRUD operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from rulerepo_server.core.deps import get_rule_service
from rulerepo_server.schemas.rule import RuleCreate, RuleUpdate
from rulerepo_server.services.rule_service import RuleService

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", status_code=201)
async def create_rule(
    data: RuleCreate,
    project_id: str | None = Query(default=None),
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Create a new rule."""
    return await service.create_rule(data, project_id=project_id)


@router.get("")
async def list_rules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_id: str | None = Query(default=None),
    modality: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """List rules with optional filters and pagination."""
    return await service.list_rules(
        page=page,
        page_size=page_size,
        project_id=project_id,
        modality=modality,
        severity=severity,
        status=status,
    )


@router.get("/{rule_id}")
async def get_rule(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Get a single rule by ID."""
    return await service.get_rule(rule_id)


@router.patch("/{rule_id}")
async def update_rule(
    rule_id: UUID,
    data: RuleUpdate,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Update an existing rule."""
    return await service.update_rule(rule_id, data)


@router.post("/{rule_id}/retire")
async def retire_rule(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Retire a rule (soft-delete via effective_period.valid_until)."""
    return await service.retire_rule(rule_id)


@router.get("/{rule_id}/revisions")
async def get_revisions(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> list[dict]:
    """Get the revision history for a rule."""
    return await service.get_revisions(rule_id)


@router.get("/{rule_id}/relationships")
async def get_relationships(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> list[dict]:
    """Get all relationships involving a rule."""
    return await service.get_relationships(rule_id)


@router.get("/{rule_id}/graph")
async def get_graph(
    rule_id: UUID,
    depth: int = Query(default=1, ge=1, le=5),
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Get the relationship subgraph around a rule."""
    return await service.get_graph(rule_id, depth=depth)
