"""Attribute-Based Access Control (ABAC) policy domain types.

Pure domain — no imports from services/, adapters/, or api/.

ABAC policies express fine-grained access rules that go beyond simple
RBAC.  The policy engine evaluates them at runtime against the requesting
principal, the target resource, and the action being performed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PolicyEffect(StrEnum):
    """The effect of a matched ABAC policy."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyCondition:
    """A single condition within an ABAC policy.

    Attributes:
        attribute: Dot-separated attribute path on the evaluation context
                   (e.g. ``principal.clearance``, ``resource.classification``).
        operator: Comparison operator — one of eq, ne, in, contains, gte, lte.
        value: The value to compare against.  Type depends on the operator.
    """

    attribute: str
    operator: str  # eq | ne | in | contains | gte | lte
    value: Any = None


@dataclass(frozen=True)
class ABACPolicy:
    """A declarative access-control policy evaluated by the ABAC engine.

    Policies are matched against a request context.  When multiple
    policies match, the one with the highest ``priority`` wins.  If
    priorities tie, DENY takes precedence over ALLOW.

    Attributes:
        id: Unique policy identifier.
        name: Human-readable policy name.
        effect: ALLOW or DENY.
        conditions: All conditions must be true for the policy to match.
        resource_type: The resource type this policy applies to (e.g. "rule").
        actions: The actions this policy governs (e.g. ["read", "write"]).
        priority: Higher values take precedence. Default 0.
        description: Free-text description of the policy's purpose.
    """

    id: str
    name: str
    effect: PolicyEffect
    conditions: list[PolicyCondition] = field(default_factory=list)
    resource_type: str = "*"
    actions: list[str] = field(default_factory=lambda: ["*"])
    priority: int = 0
    description: str = ""


@dataclass(frozen=True)
class PolicyDecision:
    """The result of evaluating ABAC policies for a request.

    Attributes:
        effect: The final effect — ALLOW or DENY.
        matching_policies: IDs of all policies that matched the request.
        reason: Human-readable explanation of why this decision was reached.
    """

    effect: PolicyEffect
    matching_policies: list[str] = field(default_factory=list)
    reason: str = ""
