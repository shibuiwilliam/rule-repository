"""ABAC governance policy resolver.

Evaluates governance policies to determine access decisions.
Resolution order: explicit deny > explicit allow > inherited allow > default deny.

See CLAUDE.md §14.10.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.governance import GovernancePolicy

logger = get_logger(__name__)


@dataclass(frozen=True)
class AccessDecision:
    """Result of a governance policy evaluation."""

    allowed: bool
    reason: str
    matching_policy_id: str | None = None
    principal: str = ""
    action: str = ""
    domain: str | None = None


class GovernanceResolver:
    """Resolves ABAC governance policies for access decisions.

    Resolution order:
    1. Explicit deny (domain + org_unit match) -> DENY
    2. Explicit allow (domain + org_unit match) -> ALLOW
    3. Inherited allow (parent org_unit match) -> ALLOW
    4. Default deny -> DENY
    """

    def __init__(self, policies: list[GovernancePolicy] | None = None) -> None:
        self._policies = list(policies) if policies else []

    def add_policy(self, policy: GovernancePolicy) -> None:
        """Add a policy to the resolver."""
        self._policies.append(policy)

    def evaluate(
        self,
        *,
        principal: str,
        action: str,
        domain: str | None = None,
        org_unit: str | None = None,
    ) -> AccessDecision:
        """Evaluate whether a principal can perform an action.

        Args:
            principal: The principal requesting access
                (e.g., "user:alice", "group:legal-team").
            action: The action being performed
                (e.g., "rule.read", "rule.edit").
            domain: The domain of the resource (e.g., "legal", "hr").
            org_unit: The org unit of the resource.

        Returns:
            AccessDecision with the result and reasoning.
        """
        # Step 1: Check for explicit deny
        for policy in self._policies:
            if policy.effect != "deny":
                continue
            if not self._matches_action(policy, action):
                continue
            if not self._matches_principal(policy, principal):
                continue
            if self._matches_scope(policy, domain, org_unit):
                return AccessDecision(
                    allowed=False,
                    reason=f"Denied by policy: {policy.description or policy.id}",
                    matching_policy_id=policy.id,
                    principal=principal,
                    action=action,
                    domain=domain,
                )

        # Step 2: Check for explicit allow
        for policy in self._policies:
            if policy.effect != "allow":
                continue
            if not self._matches_action(policy, action):
                continue
            if not self._matches_principal(policy, principal):
                continue
            if self._matches_scope(policy, domain, org_unit):
                return AccessDecision(
                    allowed=True,
                    reason=f"Allowed by policy: {policy.description or policy.id}",
                    matching_policy_id=policy.id,
                    principal=principal,
                    action=action,
                    domain=domain,
                )

        # Step 3: Check for inherited allow (parent org_unit)
        if org_unit and "/" in org_unit:
            parent_org = org_unit.rsplit("/", 1)[0]
            parent_decision = self.evaluate(
                principal=principal,
                action=action,
                domain=domain,
                org_unit=parent_org,
            )
            if parent_decision.allowed:
                return AccessDecision(
                    allowed=True,
                    reason=(f"Inherited from parent org_unit '{parent_org}': {parent_decision.reason}"),
                    matching_policy_id=parent_decision.matching_policy_id,
                    principal=principal,
                    action=action,
                    domain=domain,
                )

        # Step 4: Default deny
        return AccessDecision(
            allowed=False,
            reason="Default deny: no matching policy found",
            principal=principal,
            action=action,
            domain=domain,
        )

    def _matches_action(self, policy: GovernancePolicy, action: str) -> bool:
        """Check if a policy matches the requested action."""
        return policy.action == action or policy.action == ""

    def _matches_principal(self, policy: GovernancePolicy, principal: str) -> bool:
        """Check if a policy matches the requesting principal."""
        if not policy.principals:
            return True  # No principal restriction = matches all
        return principal in policy.principals or "group:all" in policy.principals

    def _matches_scope(
        self,
        policy: GovernancePolicy,
        domain: str | None,
        org_unit: str | None,
    ) -> bool:
        """Check if a policy's scope matches the resource scope."""
        # None in policy = matches all
        if policy.domain is not None and policy.domain != domain:
            return False
        if policy.org_unit is not None:
            if org_unit is None:
                return False
            if policy.org_unit != org_unit and not org_unit.startswith(policy.org_unit + "/"):
                return False
        return True
