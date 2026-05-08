"""Segregation of Duties (SoD) enforcement.

Detects conflicts of interest in approval and enactment workflows.
For example, the person who proposes a rule change must not be the
sole approver of that same change.

Usage::

    violation = check_segregation_of_duties(
        actor_id="user-42",
        action="approve",
        resource_id="rule-7",
        history=[
            {"action": "propose", "actor_id": "user-42", "resource_id": "rule-7"},
        ],
    )
    if violation is not None:
        raise AuthorizationError(violation.description)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SoDViolation:
    """Describes a segregation-of-duties violation.

    Attributes:
        rule_name: The name of the SoD constraint that was violated.
        actor: The actor who triggered the violation.
        conflicting_action: The action that conflicts with the actor's prior action.
        description: Human-readable explanation.
    """

    rule_name: str
    actor: str
    conflicting_action: str
    description: str


# Type for an SoD constraint function.
# (actor_id, action, resource_id, history) -> SoDViolation | None
SoDConstraintFn = Callable[[str, str, str, list[dict[str, Any]]], SoDViolation | None]


# ---------------------------------------------------------------------------
# Built-in SoD constraints
# ---------------------------------------------------------------------------


def _proposer_ne_approver(
    actor_id: str,
    action: str,
    resource_id: str,
    history: list[dict[str, Any]],
) -> SoDViolation | None:
    """Proposer must not be the sole approver of their own proposal."""
    if action != "approve":
        return None
    for entry in history:
        if (
            entry.get("action") == "propose"
            and entry.get("actor_id") == actor_id
            and entry.get("resource_id") == resource_id
        ):
            return SoDViolation(
                rule_name="proposer_ne_approver",
                actor=actor_id,
                conflicting_action=action,
                description=(
                    f"Actor '{actor_id}' cannot approve resource '{resource_id}' because they are the proposer"
                ),
            )
    return None


def _approver_ne_enactor(
    actor_id: str,
    action: str,
    resource_id: str,
    history: list[dict[str, Any]],
) -> SoDViolation | None:
    """Approver must not also enact (publish/activate) the change."""
    if action != "enact":
        return None
    for entry in history:
        if (
            entry.get("action") == "approve"
            and entry.get("actor_id") == actor_id
            and entry.get("resource_id") == resource_id
        ):
            return SoDViolation(
                rule_name="approver_ne_enactor",
                actor=actor_id,
                conflicting_action=action,
                description=(f"Actor '{actor_id}' cannot enact resource '{resource_id}' because they approved it"),
            )
    return None


def _author_ne_sole_approver(
    actor_id: str,
    action: str,
    resource_id: str,
    history: list[dict[str, Any]],
) -> SoDViolation | None:
    """Author must not be the sole approver of their own content."""
    if action != "approve":
        return None
    for entry in history:
        if (
            entry.get("action") == "author"
            and entry.get("actor_id") == actor_id
            and entry.get("resource_id") == resource_id
        ):
            # Check if there are other approvers in history
            other_approvers = [
                e
                for e in history
                if e.get("action") == "approve"
                and e.get("resource_id") == resource_id
                and e.get("actor_id") != actor_id
            ]
            if not other_approvers:
                return SoDViolation(
                    rule_name="author_ne_sole_approver",
                    actor=actor_id,
                    conflicting_action=action,
                    description=(
                        f"Actor '{actor_id}' cannot be the sole approver of resource "
                        f"'{resource_id}' because they authored it"
                    ),
                )
    return None


# Ordered list of all built-in SoD constraints.
SOD_RULES: list[SoDConstraintFn] = [
    _proposer_ne_approver,
    _approver_ne_enactor,
    _author_ne_sole_approver,
]


def check_segregation_of_duties(
    actor_id: str,
    action: str,
    resource_id: str,
    history: list[dict[str, Any]],
) -> SoDViolation | None:
    """Check all SoD rules and return the first violation, if any.

    Args:
        actor_id: The principal attempting the action.
        action: The action being performed (e.g. "approve", "enact").
        resource_id: The resource being acted upon.
        history: Prior actions on this resource, each a dict with at least
                 ``action``, ``actor_id``, and ``resource_id`` keys.

    Returns:
        A SoDViolation if any constraint is violated, else None.
    """
    for constraint in SOD_RULES:
        violation = constraint(actor_id, action, resource_id, history)
        if violation is not None:
            return violation
    return None
