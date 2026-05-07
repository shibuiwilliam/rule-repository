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
