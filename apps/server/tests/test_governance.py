"""Tests for ABAC governance resolver."""

from rulerepo_server.domain.governance import GOVERNANCE_ACTIONS, GovernancePolicy
from rulerepo_server.services.governance.resolver import (
    AccessDecision,
    GovernanceResolver,
)


class TestGovernancePolicy:
    def test_create_policy(self) -> None:
        policy = GovernancePolicy(
            id="p1",
            domain="legal",
            action="rule.edit",
            principals=["group:legal-team"],
            effect="allow",
        )
        assert policy.domain == "legal"
        assert policy.effect == "allow"

    def test_valid_actions(self) -> None:
        assert "rule.read" in GOVERNANCE_ACTIONS
        assert "rule.edit" in GOVERNANCE_ACTIONS
        assert "rule.approve" in GOVERNANCE_ACTIONS


class TestGovernanceResolver:
    def test_default_deny(self) -> None:
        resolver = GovernanceResolver()
        decision = resolver.evaluate(
            principal="user:alice",
            action="rule.edit",
            domain="legal",
        )
        assert not decision.allowed
        assert "Default deny" in decision.reason

    def test_explicit_allow(self) -> None:
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    domain="legal",
                    action="rule.edit",
                    principals=["group:legal-team"],
                    effect="allow",
                ),
            ]
        )
        decision = resolver.evaluate(
            principal="group:legal-team",
            action="rule.edit",
            domain="legal",
        )
        assert decision.allowed

    def test_explicit_deny_overrides_allow(self) -> None:
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    action="rule.read",
                    principals=["group:all"],
                    effect="allow",
                ),
                GovernancePolicy(
                    id="p2",
                    domain="legal",
                    action="rule.read",
                    principals=["group:engineering"],
                    effect="deny",
                    description="Engineering cannot read legal rules",
                ),
            ]
        )
        decision = resolver.evaluate(
            principal="group:engineering",
            action="rule.read",
            domain="legal",
        )
        assert not decision.allowed
        assert "Engineering cannot read" in decision.reason

    def test_global_read_policy(self) -> None:
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    action="rule.read",
                    principals=["group:all"],
                    effect="allow",
                ),
            ]
        )
        decision = resolver.evaluate(
            principal="user:anyone",
            action="rule.read",
            domain="hr",
        )
        assert decision.allowed

    def test_inherited_org_unit(self) -> None:
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    domain="hr",
                    org_unit="acme",
                    action="rule.read",
                    principals=["user:bob"],
                    effect="allow",
                ),
            ]
        )
        decision = resolver.evaluate(
            principal="user:bob",
            action="rule.read",
            domain="hr",
            org_unit="acme/jp/tokyo",
        )
        assert decision.allowed
        assert "Inherited" in decision.reason or "Allowed" in decision.reason

    def test_domain_mismatch(self) -> None:
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    domain="legal",
                    action="rule.edit",
                    principals=["user:alice"],
                    effect="allow",
                ),
            ]
        )
        decision = resolver.evaluate(
            principal="user:alice",
            action="rule.edit",
            domain="hr",
        )
        assert not decision.allowed

    def test_cross_domain_scenario(self) -> None:
        """Legal can edit legal rules, read all. Engineering can edit engineering, read all."""
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    action="rule.read",
                    principals=["group:all"],
                    effect="allow",
                ),
                GovernancePolicy(
                    id="p2",
                    domain="legal",
                    action="rule.edit",
                    principals=["group:legal-team"],
                    effect="allow",
                ),
                GovernancePolicy(
                    id="p3",
                    domain="engineering",
                    action="rule.edit",
                    principals=["group:engineering"],
                    effect="allow",
                ),
            ]
        )

        # Legal can read engineering rules
        assert resolver.evaluate(
            principal="group:legal-team",
            action="rule.read",
            domain="engineering",
        ).allowed
        # Legal can edit legal rules
        assert resolver.evaluate(
            principal="group:legal-team",
            action="rule.edit",
            domain="legal",
        ).allowed
        # Legal cannot edit engineering rules
        assert not resolver.evaluate(
            principal="group:legal-team",
            action="rule.edit",
            domain="engineering",
        ).allowed
        # Engineering can edit engineering rules
        assert resolver.evaluate(
            principal="group:engineering",
            action="rule.edit",
            domain="engineering",
        ).allowed
        # Engineering cannot edit legal rules
        assert not resolver.evaluate(
            principal="group:engineering",
            action="rule.edit",
            domain="legal",
        ).allowed

    def test_add_policy(self) -> None:
        resolver = GovernanceResolver()
        decision = resolver.evaluate(principal="user:alice", action="rule.read", domain="hr")
        assert not decision.allowed

        resolver.add_policy(
            GovernancePolicy(
                id="p1",
                action="rule.read",
                principals=["user:alice"],
                effect="allow",
            )
        )
        decision = resolver.evaluate(principal="user:alice", action="rule.read", domain="hr")
        assert decision.allowed

    def test_wildcard_action_policy(self) -> None:
        """A policy with empty action matches any action."""
        resolver = GovernanceResolver(
            policies=[
                GovernancePolicy(
                    id="p1",
                    domain="finance",
                    action="",
                    principals=["group:finance-admins"],
                    effect="allow",
                ),
            ]
        )
        assert resolver.evaluate(
            principal="group:finance-admins",
            action="rule.edit",
            domain="finance",
        ).allowed
        assert resolver.evaluate(
            principal="group:finance-admins",
            action="rule.approve",
            domain="finance",
        ).allowed

    def test_access_decision_fields(self) -> None:
        decision = AccessDecision(
            allowed=True,
            reason="test",
            matching_policy_id="p1",
            principal="user:alice",
            action="rule.read",
            domain="legal",
        )
        assert decision.allowed
        assert decision.matching_policy_id == "p1"
        assert decision.principal == "user:alice"
