"""Department authorization helpers — CLAUDE.md §14.7.

Provides ``can_view``, ``can_edit``, ``can_approve``, and ``visible_departments``
functions used by API middleware and service layers to enforce department-level
access control.

Department RBAC is non-bypassable (CLAUDE.md §13 rule 18): every endpoint
that returns or mutates rules must apply department visibility.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import CapacityAssignmentModel
from rulerepo_server.domain.department import Capacity, capacity_rank


async def visible_departments(session: AsyncSession, user_id: str) -> set[str]:
    """Return the set of department IDs the user has any capacity in.

    The ``public`` pseudo-department is always visible to all users.

    Args:
        session: Database session.
        user_id: The authenticated user's identifier.

    Returns:
        Set of department IDs (including implicit ``public``).
    """
    stmt = select(CapacityAssignmentModel.department_id).where(
        CapacityAssignmentModel.user_id == user_id,
    )
    result = await session.execute(stmt)
    dept_ids = {str(row[0]) for row in result.all()}

    # Public is always visible
    dept_ids.add("public")
    return dept_ids


async def user_capacity_in(session: AsyncSession, user_id: str, department_id: str) -> Capacity | None:
    """Return the user's capacity in a specific department, or None.

    Args:
        session: Database session.
        user_id: The authenticated user's identifier.
        department_id: The department to check.

    Returns:
        The user's Capacity in the department, or None if no assignment.
    """
    stmt = select(CapacityAssignmentModel).where(
        CapacityAssignmentModel.user_id == user_id,
        CapacityAssignmentModel.department_id == department_id,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return Capacity(row.capacity)


async def can_view(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can view rules in a department.

    Any capacity (SUBSCRIBER, AUDITOR, REVIEWER, OWNER) grants view access.
    Rules in the ``public`` pseudo-department are always viewable.

    Args:
        session: Database session.
        user_id: The authenticated user.
        rule_department_id: Department that owns the rule.

    Returns:
        True if the user can view rules in that department.
    """
    if rule_department_id == "public":
        return True

    cap = await user_capacity_in(session, user_id, rule_department_id)
    return cap is not None


async def can_edit(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can edit rules in a department.

    Requires REVIEWER or OWNER capacity.

    Args:
        session: Database session.
        user_id: The authenticated user.
        rule_department_id: Department that owns the rule.

    Returns:
        True if the user can edit rules in that department.
    """
    cap = await user_capacity_in(session, user_id, rule_department_id)
    if cap is None:
        return False
    return capacity_rank(cap) >= capacity_rank(Capacity.REVIEWER)


async def can_approve(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can approve rules/proposals in a department.

    Requires OWNER capacity.

    Args:
        session: Database session.
        user_id: The authenticated user.
        rule_department_id: Department that owns the rule.

    Returns:
        True if the user can approve in that department.
    """
    cap = await user_capacity_in(session, user_id, rule_department_id)
    if cap is None:
        return False
    return capacity_rank(cap) >= capacity_rank(Capacity.OWNER)
