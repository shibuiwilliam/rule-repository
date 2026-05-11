"""REST API routes for Department, Capacity, and Policy management."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.domain.department import Action, Capacity, DepartmentPolicy, Principal
from rulerepo_server.schemas.department import (
    CapacityAssign,
    CapacityAssignmentResponse,
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    RuleOwnershipResponse,
    RuleOwnershipSet,
)
from rulerepo_server.services.departments.authz import (
    get_policies_for_department,
    set_policies,
)
from rulerepo_server.services.departments.service import DepartmentService

router = APIRouter(tags=["departments"])


async def _get_department_service(
    session: AsyncSession = Depends(get_db_session),
) -> DepartmentService:
    return DepartmentService(session)


# ---------------------------------------------------------------------------
# Department CRUD
# ---------------------------------------------------------------------------


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    service: DepartmentService = Depends(_get_department_service),
) -> dict:
    """Create a new department."""
    dept = await service.create_department(
        name=body.name,
        type=body.type,
        parent_id=body.parent_id,
        head=body.head,
        cost_center=body.cost_center,
        locale=body.locale,
    )
    return _dept_to_dict(dept)


@router.get("/departments", response_model=DepartmentListResponse)
async def list_departments(
    service: DepartmentService = Depends(_get_department_service),
) -> dict:
    """List all departments."""
    departments = await service.list_departments()
    return {
        "departments": [_dept_to_dict(d) for d in departments],
        "total": len(departments),
    }


@router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: str,
    service: DepartmentService = Depends(_get_department_service),
) -> dict:
    """Get a department by ID."""
    dept = await service.get_department(department_id)
    if dept is None:
        raise NotFoundError("Department", department_id)
    return _dept_to_dict(dept)


# ---------------------------------------------------------------------------
# Capacity assignments
# ---------------------------------------------------------------------------


@router.post(
    "/departments/{department_id}/capacities",
    response_model=CapacityAssignmentResponse,
    status_code=201,
)
async def assign_capacity(
    department_id: str,
    body: CapacityAssign,
    service: DepartmentService = Depends(_get_department_service),
) -> dict:
    """Assign a capacity to a user within a department."""
    assignment = await service.assign_capacity(
        department_id=department_id,
        user_id=body.user_id,
        capacity=body.capacity,
        rule_filter=body.rule_filter,
    )
    return {
        "department_id": assignment.department_id,
        "user_id": assignment.user_id,
        "capacity": assignment.capacity.value,
        "rule_filter": assignment.rule_filter,
    }


# ---------------------------------------------------------------------------
# Rule ownership
# ---------------------------------------------------------------------------


@router.post(
    "/rules/{rule_id}/ownership",
    response_model=RuleOwnershipResponse,
    status_code=201,
)
async def set_rule_ownership(
    rule_id: str,
    body: RuleOwnershipSet,
    service: DepartmentService = Depends(_get_department_service),
) -> dict:
    """Set the owning department for a rule."""
    ownership = await service.set_rule_ownership(
        rule_id=rule_id,
        department_id=body.department_id,
        delegated_to=body.delegated_to,
    )
    return {
        "rule_id": ownership.rule_id,
        "owner_department_id": ownership.owner_department_id,
        "delegated_to": ownership.delegated_to,
    }


@router.get(
    "/rules/{rule_id}/ownership",
    response_model=RuleOwnershipResponse,
)
async def get_rule_ownership(
    rule_id: str,
    service: DepartmentService = Depends(_get_department_service),
) -> dict:
    """Get the ownership record for a rule."""
    ownership = await service.get_rule_ownership(rule_id)
    if ownership is None:
        raise NotFoundError("RuleOwnership", rule_id)
    return {
        "rule_id": ownership.rule_id,
        "owner_department_id": ownership.owner_department_id,
        "delegated_to": ownership.delegated_to,
    }


# ---------------------------------------------------------------------------
# Policy management (IMPROVEMENT.md §3 Proposal 10)
# ---------------------------------------------------------------------------


class PrincipalPayload(BaseModel):
    """A (department, capacity) pair in a policy."""

    department: str = Field(..., description="Department ID, '_same_' for same-dept, '*' for any")
    capacity: Capacity


class PolicyPayload(BaseModel):
    """A single policy entry."""

    action: Action
    allowed_principals: list[PrincipalPayload]


class PoliciesResponse(BaseModel):
    """Response for GET /departments/{dept}/policies."""

    owner_department: str
    policies: list[PolicyPayload]


class PoliciesUpdateRequest(BaseModel):
    """Request for PUT /departments/{dept}/policies."""

    policies: list[PolicyPayload]


@router.get("/departments/{department_id}/policies", response_model=PoliciesResponse)
async def get_department_policies(department_id: str) -> dict[str, Any]:
    """Get the active policies for a department.

    Returns the policies that control who can READ, EDIT, APPROVE,
    EVALUATE, and DELETE resources owned by this department.
    """
    dept_policies = get_policies_for_department(department_id)
    return {
        "owner_department": department_id,
        "policies": [
            {
                "action": p.action.value,
                "allowed_principals": [
                    {"department": pr.department, "capacity": pr.capacity.value} for pr in p.allowed_principals
                ],
            }
            for p in dept_policies
        ],
    }


@router.put("/departments/{department_id}/policies", response_model=PoliciesResponse)
async def update_department_policies(
    department_id: str,
    body: PoliciesUpdateRequest,
    service: DepartmentService = Depends(_get_department_service),
) -> dict[str, Any]:
    """Replace the policies for a department.

    Only replaces policies for the specified department. Policies for
    other departments are unchanged.
    """
    # Verify department exists
    dept = await service.get_department(department_id)
    if dept is None:
        raise NotFoundError("Department", department_id)

    from rulerepo_server.services.departments.authz import get_policies

    # Rebuild: keep policies for other departments, replace this one's
    current = get_policies()
    other_policies = [p for p in current if p.owner_department != department_id]
    new_policies = [
        DepartmentPolicy(
            owner_department=department_id,
            action=pp.action,
            allowed_principals=[
                Principal(department=pr.department, capacity=pr.capacity) for pr in pp.allowed_principals
            ],
        )
        for pp in body.policies
    ]
    set_policies(other_policies + new_policies)

    return {
        "owner_department": department_id,
        "policies": [
            {
                "action": p.action.value,
                "allowed_principals": [
                    {"department": pr.department, "capacity": pr.capacity.value} for pr in p.allowed_principals
                ],
            }
            for p in new_policies
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dept_to_dict(dept) -> dict:  # type: ignore[no-untyped-def]
    """Convert a Department domain object to a dict for response."""
    return {
        "id": dept.id,
        "name": dept.name,
        "type": dept.type.value,
        "parent_id": dept.parent_id,
        "head": dept.head,
        "cost_center": dept.cost_center,
        "locale": dept.locale,
    }
