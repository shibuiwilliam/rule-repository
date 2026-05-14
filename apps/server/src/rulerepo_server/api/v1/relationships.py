"""REST API routes for rule relationship management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from rulerepo_server.core.deps import get_rule_service, require_department_action
from rulerepo_server.domain.department import Action
from rulerepo_server.schemas.rule import RelationshipCreate
from rulerepo_server.services.rule_service import RuleService

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post("", status_code=201, dependencies=[Depends(require_department_action(Action.EDIT))])
async def create_relationship(
    data: RelationshipCreate,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Create a relationship between two rules."""
    return await service.add_relationship(data.source_id, data.target_id, data.relationship_type)


@router.delete("", dependencies=[Depends(require_department_action(Action.EDIT))])
async def delete_relationship(
    source_id: UUID = Query(...),
    target_id: UUID = Query(...),
    relationship_type: str = Query(...),
    service: RuleService = Depends(get_rule_service),
) -> dict[str, str]:
    """Delete a specific relationship between two rules."""
    await service.remove_relationship(source_id, target_id, relationship_type)
    return {"status": "deleted"}
