"""Domain types for the organizational department and capacity model.

Pure domain — no imports from services/, adapters/, or api/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DepartmentType(StrEnum):
    """Well-known department categories."""

    LEGAL = "legal"
    HR = "hr"
    FINANCE = "finance"
    SALES = "sales"
    MARKETING = "marketing"
    IT = "it"
    OPERATIONS = "operations"
    RND = "rnd"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class Capacity(StrEnum):
    """User role relative to a department.

    Ordered from highest to lowest privilege.
    """

    OWNER = "owner"
    REVIEWER = "reviewer"
    SUBSCRIBER = "subscriber"
    AUDITOR = "auditor"


# Capacity ordering for privilege comparison
_CAPACITY_RANK: dict[Capacity, int] = {
    Capacity.OWNER: 4,
    Capacity.REVIEWER: 3,
    Capacity.AUDITOR: 2,
    Capacity.SUBSCRIBER: 1,
}


def capacity_rank(cap: Capacity) -> int:
    """Return numeric rank for capacity comparison (higher = more privileged)."""
    return _CAPACITY_RANK.get(cap, 0)


@dataclass(frozen=True)
class Department:
    """An organizational unit that owns rules and assigns capacities."""

    id: str
    name: str
    type: DepartmentType
    parent_id: str | None = None
    head: str = ""  # user_id of department head
    cost_center: str | None = None
    locale: str | None = None


@dataclass(frozen=True)
class RuleOwnership:
    """Binds a rule to an owning department with optional delegation."""

    rule_id: str
    owner_department_id: str
    delegated_to: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CapacityAssignment:
    """Binds a user to a department with a specific capacity."""

    department_id: str
    user_id: str
    capacity: Capacity
    rule_filter: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# ABAC-style policy model (IMPROVEMENT.md §3 Proposal 10)
# ---------------------------------------------------------------------------


class Action(StrEnum):
    """Actions that can be performed on rules owned by a department."""

    READ = "read"
    EDIT = "edit"
    APPROVE = "approve"
    EVALUATE = "evaluate"
    DELETE = "delete"


@dataclass(frozen=True)
class Principal:
    """An (department, capacity) pair that identifies who can act.

    ``department`` can be:
    - A specific department ID  → matches only that department
    - ``"*"``                   → matches any department (cross-department)
    - ``"_same_"``              → matches the same department as the resource owner
    """

    department: str
    capacity: Capacity


@dataclass(frozen=True)
class DepartmentPolicy:
    """Maps (owner_department, action) to the set of principals allowed to perform it.

    Attributes:
        owner_department: The department that owns the resource.
            ``"*"`` means this policy applies to all departments (default policy).
        action: The action being controlled.
        allowed_principals: List of (department, capacity) pairs that may
            perform this action on resources owned by ``owner_department``.
    """

    owner_department: str
    action: Action
    allowed_principals: list[Principal] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default policy set
# ---------------------------------------------------------------------------

# Sentinel values for policy matching
_SAME_DEPT = "_same_"
_ANY_DEPT = "*"


def default_policies() -> list[DepartmentPolicy]:
    """Return the default ABAC policy set.

    Same-department OWNER  → all actions
    Same-department REVIEWER → READ, EDIT, EVALUATE
    Same-department SUBSCRIBER → READ
    Same-department AUDITOR → READ, EVALUATE
    Cross-department (any capacity) → READ only
    """
    policies: list[DepartmentPolicy] = []

    # Same-department policies (apply to any owner department)
    for action in Action:
        principals: list[Principal] = []

        # OWNER can do everything
        principals.append(Principal(department=_SAME_DEPT, capacity=Capacity.OWNER))

        # REVIEWER can read, edit, and evaluate
        if action in (Action.READ, Action.EDIT, Action.EVALUATE):
            principals.append(Principal(department=_SAME_DEPT, capacity=Capacity.REVIEWER))

        if action in (Action.READ, Action.EVALUATE):
            principals.append(Principal(department=_SAME_DEPT, capacity=Capacity.AUDITOR))

        if action == Action.READ:
            principals.append(Principal(department=_SAME_DEPT, capacity=Capacity.SUBSCRIBER))
            # Cross-department: any capacity grants READ
            for cap in Capacity:
                principals.append(Principal(department=_ANY_DEPT, capacity=cap))

        policies.append(
            DepartmentPolicy(
                owner_department=_ANY_DEPT,
                action=action,
                allowed_principals=principals,
            )
        )

    return policies
