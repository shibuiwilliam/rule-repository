"""ABAC-style governance policies per PROJECT.md §6.9.

Resolution order: explicit deny > explicit allow > inherited allow > default deny.

This module provides a higher-level, domain-oriented governance model
that complements the general-purpose ABAC engine in ``domain.abac``.
While ``ABACPolicy`` supports arbitrary condition-based matching,
``GovernancePolicy`` is purpose-built for the common case of granting
or denying principals access to rules by domain and org_unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class GovernancePolicy:
    """An attribute-based access control policy.

    Policies are evaluated by the governance resolver to determine
    whether a principal can perform an action on rules in a given
    domain and org_unit.
    """

    id: str = ""
    domain: str | None = None  # None = applies to all domains
    org_unit: str | None = None  # None = applies to all units
    action: str = ""  # "rule.read" | "rule.edit" | "rule.approve" | "rule.evaluate"
    principals: list[str] = field(default_factory=list)
    # "group:legal-team", "role:approver", "user:alice"
    effect: Literal["allow", "deny"] = "allow"
    description: str = ""


# Valid actions
GOVERNANCE_ACTIONS = frozenset(
    {
        "rule.read",
        "rule.edit",
        "rule.approve",
        "rule.evaluate",
        "rule.create",
        "rule.retire",
    }
)
