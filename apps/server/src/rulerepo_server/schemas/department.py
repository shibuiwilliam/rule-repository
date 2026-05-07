"""Pydantic request/response schemas for Department and Capacity endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rulerepo_server.domain.department import Capacity, DepartmentType

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class DepartmentCreate(BaseModel):
    """Schema for creating a new department."""

    name: str = Field(..., min_length=1, max_length=255, description="Department name")
    type: DepartmentType = DepartmentType.CUSTOM
    parent_id: str | None = None
    head: str = Field(default="", description="User ID of department head")
    cost_center: str | None = None
    locale: str | None = None


class CapacityAssign(BaseModel):
    """Schema for assigning a capacity to a user in a department."""

    user_id: str = Field(..., min_length=1, description="User ID to assign")
    capacity: Capacity = Capacity.SUBSCRIBER
    rule_filter: dict | None = None


class RuleOwnershipSet(BaseModel):
    """Schema for setting rule ownership."""

    department_id: str = Field(..., min_length=1, description="Owning department ID")
    delegated_to: list[str] = Field(default_factory=list, description="Delegated user IDs")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DepartmentResponse(BaseModel):
    """Response schema for a department."""

    id: str
    name: str
    type: DepartmentType
    parent_id: str | None = None
    head: str
    cost_center: str | None = None
    locale: str | None = None


class DepartmentListResponse(BaseModel):
    """Response schema for listing departments."""

    departments: list[DepartmentResponse]
    total: int


class CapacityAssignmentResponse(BaseModel):
    """Response schema for a capacity assignment."""

    department_id: str
    user_id: str
    capacity: Capacity
    rule_filter: dict | None = None


class RuleOwnershipResponse(BaseModel):
    """Response schema for rule ownership."""

    rule_id: str
    owner_department_id: str
    delegated_to: list[str] = Field(default_factory=list)


class ApproversResponse(BaseModel):
    """Response schema for resolved approvers."""

    rule_id: str
    approver_ids: list[str]
    severity: str
