"""Department authorization helpers — CLAUDE.md §14.7.

Provides policy-based authorization functions used by API middleware and
service layers to enforce department-level access control.

Department RBAC is non-bypassable (CLAUDE.md §13 rule 19): every endpoint
that returns or mutates rules must apply department visibility.

Authorization is ABAC-style: policies map (owner_department, action) to
allowed (principal_department, capacity) pairs. See IMPROVEMENT.md §3
Proposal 10.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import CapacityAssignmentModel
from rulerepo_server.domain.department import (
    _ANY_DEPT,
    _SAME_DEPT,
    Action,
    Capacity,
    DepartmentPolicy,
    Principal,
    default_policies,
)

# ---------------------------------------------------------------------------
# Policy store (in-memory; persisted policies can overlay via set_policies)
# ---------------------------------------------------------------------------

_active_policies: list[DepartmentPolicy] | None = None


def get_policies() -> list[DepartmentPolicy]:
    """Return the active policy set (defaults if no overrides)."""
    global _active_policies
    if _active_policies is None:
        _active_policies = default_policies()
    return _active_policies


def set_policies(policies: list[DepartmentPolicy]) -> None:
    """Replace the active policy set (used by API and tests)."""
    global _active_policies
    _active_policies = list(policies)


def reset_policies() -> None:
    """Reset to default policies (useful for tests)."""
    global _active_policies
    _active_policies = None


def get_policies_for_department(owner_department: str) -> list[DepartmentPolicy]:
    """Return policies applicable to a specific owner department.

    Matches both department-specific policies and wildcard (``*``) policies.
    """
    result: list[DepartmentPolicy] = []
    for p in get_policies():
        if p.owner_department == owner_department or p.owner_department == _ANY_DEPT:
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Core authorization check
# ---------------------------------------------------------------------------


async def check_permission(
    session: AsyncSession,
    user_id: str,
    rule_department_id: str,
    action: Action,
) -> bool:
    """Check if a user is allowed to perform an action on a department's resources.

    Evaluates the active policy set against the user's capacity assignments.
    A user is authorized if any policy for (rule_department_id, action) has
    a principal that matches one of the user's capacity assignments.

    Args:
        session: Database session.
        user_id: The authenticated user's identifier.
        rule_department_id: Department that owns the resource.
        action: The action being attempted.

    Returns:
        True if the user is authorized.
    """
    # Public department — anyone can READ/EVALUATE, but not mutate
    if rule_department_id == "public":
        return action in (Action.READ, Action.EVALUATE)

    # Load the user's capacity assignments across all departments
    stmt = select(CapacityAssignmentModel).where(
        CapacityAssignmentModel.user_id == user_id,
    )
    result = await session.execute(stmt)
    assignments = result.scalars().all()

    if not assignments:
        return False

    # Build a lookup: department_id → capacity
    user_capacities: dict[str, Capacity] = {}
    for a in assignments:
        user_capacities[str(a.department_id)] = Capacity(a.capacity)

    # Find applicable policies
    policies = get_policies_for_department(rule_department_id)

    for policy in policies:
        if policy.action != action:
            continue

        for principal in policy.allowed_principals:
            if _principal_matches(principal, rule_department_id, user_capacities):
                return True

    return False


def _principal_matches(
    principal: Principal,
    rule_department_id: str,
    user_capacities: dict[str, Capacity],
) -> bool:
    """Check if a user's capacity assignments match a policy principal.

    Args:
        principal: The (department, capacity) requirement.
        rule_department_id: The department that owns the resource.
        user_capacities: The user's department → capacity mapping.
    """
    if principal.department == _SAME_DEPT:
        # User must have the required capacity in the same department as the resource
        user_cap = user_capacities.get(rule_department_id)
        return user_cap is not None and user_cap == principal.capacity

    if principal.department == _ANY_DEPT:
        # User must have the required capacity in any department
        return any(cap == principal.capacity for cap in user_capacities.values())

    # Specific department
    user_cap = user_capacities.get(principal.department)
    return user_cap is not None and user_cap == principal.capacity


# ---------------------------------------------------------------------------
# Convenience wrappers (backward-compatible API)
# ---------------------------------------------------------------------------


async def visible_departments(session: AsyncSession, user_id: str) -> set[str]:
    """Return the set of department IDs the user has any capacity in.

    The ``public`` pseudo-department is always visible to all users.
    """
    stmt = select(CapacityAssignmentModel.department_id).where(
        CapacityAssignmentModel.user_id == user_id,
    )
    result = await session.execute(stmt)
    dept_ids = {str(row[0]) for row in result.all()}
    dept_ids.add("public")
    return dept_ids


async def user_capacity_in(session: AsyncSession, user_id: str, department_id: str) -> Capacity | None:
    """Return the user's capacity in a specific department, or None."""
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

    Delegates to the policy engine with ``Action.READ``.
    """
    return await check_permission(session, user_id, rule_department_id, Action.READ)


async def can_edit(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can edit rules in a department.

    Delegates to the policy engine with ``Action.EDIT``.
    """
    return await check_permission(session, user_id, rule_department_id, Action.EDIT)


async def can_approve(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can approve rules/proposals in a department.

    Delegates to the policy engine with ``Action.APPROVE``.
    """
    return await check_permission(session, user_id, rule_department_id, Action.APPROVE)


async def can_evaluate(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can evaluate rules in a department.

    Delegates to the policy engine with ``Action.EVALUATE``.
    """
    return await check_permission(session, user_id, rule_department_id, Action.EVALUATE)


async def can_delete(session: AsyncSession, user_id: str, rule_department_id: str) -> bool:
    """Check if a user can delete rules in a department.

    Delegates to the policy engine with ``Action.DELETE``.
    """
    return await check_permission(session, user_id, rule_department_id, Action.DELETE)
