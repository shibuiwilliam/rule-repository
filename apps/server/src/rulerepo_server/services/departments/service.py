"""Department and capacity management service.

Provides CRUD for departments, capacity assignments, and rule ownership,
plus resolution helpers used by proposals, intelligence, and audit.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    CapacityAssignmentModel,
    DepartmentModel,
    RuleOwnershipModel,
)
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.domain.department import (
    Capacity,
    CapacityAssignment,
    Department,
    DepartmentType,
    RuleOwnership,
    capacity_rank,
)


def _model_to_department(m: DepartmentModel) -> Department:
    """Convert a DepartmentModel ORM instance to a domain Department."""
    return Department(
        id=str(m.id),
        name=m.name,
        type=DepartmentType(m.type),
        parent_id=str(m.parent_id) if m.parent_id else None,
        head=m.head_user_id,
        cost_center=m.cost_center,
        locale=m.locale,
    )


def _model_to_ownership(m: RuleOwnershipModel) -> RuleOwnership:
    """Convert a RuleOwnershipModel ORM instance to a domain RuleOwnership."""
    return RuleOwnership(
        rule_id=str(m.rule_id),
        owner_department_id=str(m.owner_department_id),
        delegated_to=m.delegated_to or [],
    )


def _model_to_capacity_assignment(m: CapacityAssignmentModel) -> CapacityAssignment:
    """Convert a CapacityAssignmentModel to a domain CapacityAssignment."""
    return CapacityAssignment(
        department_id=str(m.department_id),
        user_id=m.user_id,
        capacity=Capacity(m.capacity),
        rule_filter=m.rule_filter,
    )


class DepartmentService:
    """Manages departments, capacity assignments, and rule ownership."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Department CRUD
    # ------------------------------------------------------------------

    async def create_department(
        self,
        name: str,
        type: DepartmentType = DepartmentType.CUSTOM,
        parent_id: str | None = None,
        head: str = "",
        cost_center: str | None = None,
        locale: str | None = None,
    ) -> Department:
        """Create a new department."""
        dept = DepartmentModel(
            id=str(uuid4()),
            name=name,
            type=type.value,
            parent_id=parent_id,
            head_user_id=head,
            cost_center=cost_center,
            locale=locale,
        )
        self._session.add(dept)
        await self._session.flush()
        return _model_to_department(dept)

    async def get_department(self, department_id: str) -> Department | None:
        """Get a department by ID, or None if not found."""
        stmt = select(DepartmentModel).where(DepartmentModel.id == department_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _model_to_department(row) if row else None

    async def list_departments(self) -> list[Department]:
        """List all departments."""
        stmt = select(DepartmentModel).order_by(DepartmentModel.name)
        result = await self._session.execute(stmt)
        return [_model_to_department(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Capacity assignment
    # ------------------------------------------------------------------

    async def assign_capacity(
        self,
        department_id: str,
        user_id: str,
        capacity: Capacity,
        rule_filter: dict | None = None,
    ) -> CapacityAssignment:
        """Assign a capacity to a user within a department.

        If the user already has a capacity in the department, it is replaced.
        """
        # Check department exists
        dept = await self.get_department(department_id)
        if dept is None:
            raise NotFoundError("Department", department_id)

        # Upsert: remove existing assignment for this user+department
        existing_stmt = select(CapacityAssignmentModel).where(
            CapacityAssignmentModel.department_id == department_id,
            CapacityAssignmentModel.user_id == user_id,
        )
        result = await self._session.execute(existing_stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.capacity = capacity.value
            existing.rule_filter = rule_filter
            await self._session.flush()
            return _model_to_capacity_assignment(existing)

        assignment = CapacityAssignmentModel(
            id=str(uuid4()),
            department_id=department_id,
            user_id=user_id,
            capacity=capacity.value,
            rule_filter=rule_filter,
        )
        self._session.add(assignment)
        await self._session.flush()
        return _model_to_capacity_assignment(assignment)

    # ------------------------------------------------------------------
    # Rule ownership
    # ------------------------------------------------------------------

    async def set_rule_ownership(
        self,
        rule_id: str,
        department_id: str,
        delegated_to: list[str] | None = None,
    ) -> RuleOwnership:
        """Set or update the owning department for a rule."""
        dept = await self.get_department(department_id)
        if dept is None:
            raise NotFoundError("Department", department_id)

        stmt = select(RuleOwnershipModel).where(RuleOwnershipModel.rule_id == rule_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.owner_department_id = department_id
            existing.delegated_to = delegated_to or []
            await self._session.flush()
            return _model_to_ownership(existing)

        ownership = RuleOwnershipModel(
            id=str(uuid4()),
            rule_id=rule_id,
            owner_department_id=department_id,
            delegated_to=delegated_to or [],
        )
        self._session.add(ownership)
        await self._session.flush()
        return _model_to_ownership(ownership)

    async def get_rule_ownership(self, rule_id: str) -> RuleOwnership | None:
        """Get ownership record for a rule."""
        stmt = select(RuleOwnershipModel).where(RuleOwnershipModel.rule_id == rule_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _model_to_ownership(row) if row else None

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    async def resolve_owner(self, rule_id: str) -> Department | None:
        """Resolve the owning department for a rule."""
        ownership = await self.get_rule_ownership(rule_id)
        if ownership is None:
            return None
        return await self.get_department(ownership.owner_department_id)

    async def resolve_approvers(self, rule_id: str, severity: str = "MEDIUM") -> list[str]:
        """Resolve user IDs who can approve changes to a rule.

        Returns users with OWNER or REVIEWER capacity in the owning department.
        For CRITICAL severity, the department head is always included.
        """
        ownership = await self.get_rule_ownership(rule_id)
        if ownership is None:
            return []

        dept = await self.get_department(ownership.owner_department_id)
        if dept is None:
            return []

        stmt = select(CapacityAssignmentModel).where(
            CapacityAssignmentModel.department_id == ownership.owner_department_id,
            CapacityAssignmentModel.capacity.in_([Capacity.OWNER.value, Capacity.REVIEWER.value]),
        )
        result = await self._session.execute(stmt)
        user_ids = [row.user_id for row in result.scalars().all()]

        # For CRITICAL severity, always include the department head
        if severity == "CRITICAL" and dept.head and dept.head not in user_ids:
            user_ids.append(dept.head)

        return user_ids

    async def resolve_audience(self, rule_id: str, capacity: Capacity) -> list[str]:
        """Resolve user IDs with a given capacity for a rule's owning department."""
        ownership = await self.get_rule_ownership(rule_id)
        if ownership is None:
            return []

        stmt = select(CapacityAssignmentModel).where(
            CapacityAssignmentModel.department_id == ownership.owner_department_id,
            CapacityAssignmentModel.capacity == capacity.value,
        )
        result = await self._session.execute(stmt)
        return [row.user_id for row in result.scalars().all()]

    async def effective_capacity(self, user_id: str, rule_id: str) -> Capacity | None:
        """Return the highest capacity a user holds for a rule's owning department.

        Returns None if the user has no capacity for the rule's department.
        """
        ownership = await self.get_rule_ownership(rule_id)
        if ownership is None:
            return None

        stmt = select(CapacityAssignmentModel).where(
            CapacityAssignmentModel.department_id == ownership.owner_department_id,
            CapacityAssignmentModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        assignments = result.scalars().all()

        if not assignments:
            return None

        # Return highest-ranked capacity
        best: Capacity | None = None
        for a in assignments:
            cap = Capacity(a.capacity)
            if best is None or capacity_rank(cap) > capacity_rank(best):
                best = cap
        return best
