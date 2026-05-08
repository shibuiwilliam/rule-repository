"""Attribute-Based Access Control (ABAC) policy engine.

Evaluates ABAC policies against a request context consisting of the
requesting principal, the target resource type and attributes, and
the action being performed.

Usage::

    engine = ABACEngine()
    engine.load_policies([policy_1, policy_2])
    decision = engine.evaluate(principal, "rule", "read", {"classification": "confidential"})
    if decision.effect == PolicyEffect.DENY:
        raise AuthorizationError(decision.reason)
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.abac import ABACPolicy, PolicyCondition, PolicyDecision, PolicyEffect
from rulerepo_server.domain.tenant import Principal

logger = get_logger(__name__)


class ABACEngine:
    """Evaluates ABAC policies to produce ALLOW / DENY decisions.

    Policies are loaded once (typically at startup or on config change)
    and evaluated per-request.  The engine is stateless beyond the
    loaded policy set.

    Resolution order when multiple policies match:
      1. Highest ``priority`` wins.
      2. On tie, DENY takes precedence over ALLOW.
    """

    def __init__(self) -> None:
        self._policies: list[ABACPolicy] = []

    def load_policies(self, policies: list[ABACPolicy]) -> None:
        """Replace the current policy set.

        Args:
            policies: The full list of ABAC policies to enforce.
        """
        self._policies = list(policies)
        logger.info("abac_policies_loaded", count=len(self._policies))

    def evaluate(
        self,
        principal: Principal,
        resource_type: str,
        action: str,
        resource_attrs: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Evaluate all matching policies and return the final decision.

        Args:
            principal: The authenticated principal making the request.
            resource_type: The type of resource (e.g. "rule", "evaluation").
            action: The action being performed (e.g. "read", "write", "delete").
            resource_attrs: Arbitrary attributes of the target resource for
                            condition matching.

        Returns:
            A PolicyDecision with the final effect and explanation.
        """
        if resource_attrs is None:
            resource_attrs = {}

        context = self._build_context(principal, resource_type, action, resource_attrs)
        matching: list[ABACPolicy] = []

        for policy in self._policies:
            if self._policy_matches(policy, resource_type, action, context):
                matching.append(policy)

        if not matching:
            # Default deny when no policy matches
            return PolicyDecision(
                effect=PolicyEffect.DENY,
                matching_policies=[],
                reason="No matching policy found — default deny",
            )

        # Sort by priority descending; on tie DENY wins
        matching.sort(key=lambda p: (p.priority, 0 if p.effect == PolicyEffect.DENY else 1), reverse=True)

        winner = matching[0]
        return PolicyDecision(
            effect=winner.effect,
            matching_policies=[p.id for p in matching],
            reason=f"Decided by policy '{winner.name}' (priority={winner.priority})",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(
        principal: Principal,
        resource_type: str,
        action: str,
        resource_attrs: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a flat evaluation context from the request components."""
        return {
            "principal.id": principal.id,
            "principal.tenant_id": principal.tenant_id,
            "principal.kind": principal.kind.value,
            "principal.clearance": principal.clearance,
            "principal.roles": principal.roles,
            "principal.groups": principal.groups,
            "principal.department_ids": principal.department_ids,
            "principal.organization_id": principal.organization_id,
            "resource.type": resource_type,
            "action": action,
            **{f"resource.{k}": v for k, v in resource_attrs.items()},
        }

    @staticmethod
    def _policy_matches(
        policy: ABACPolicy,
        resource_type: str,
        action: str,
        context: dict[str, Any],
    ) -> bool:
        """Check whether a policy's scope and conditions match the context."""
        # Resource type check
        if policy.resource_type != "*" and policy.resource_type != resource_type:
            return False

        # Action check
        if "*" not in policy.actions and action not in policy.actions:
            return False

        # All conditions must pass
        return all(_evaluate_condition(cond, context) for cond in policy.conditions)


def _evaluate_condition(condition: PolicyCondition, context: dict[str, Any]) -> bool:
    """Evaluate a single policy condition against the context.

    Args:
        condition: The condition to evaluate.
        context: The flat evaluation context dictionary.

    Returns:
        True if the condition is satisfied.
    """
    actual = context.get(condition.attribute)
    expected = condition.value
    op = condition.operator

    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "in":
        # ``actual`` is a scalar, ``expected`` is a list
        if isinstance(expected, list):
            return actual in expected
        return False
    if op == "contains":
        # ``actual`` is a list, check if ``expected`` is a member
        if isinstance(actual, list):
            return expected in actual
        if isinstance(actual, str):
            return str(expected) in actual
        return False
    if op == "gte":
        if actual is None or expected is None:
            return False
        return actual >= expected
    if op == "lte":
        if actual is None or expected is None:
            return False
        return actual <= expected

    logger.warning("unknown_abac_operator", operator=op, attribute=condition.attribute)
    return False
