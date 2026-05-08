"""Unit tests for ABAC policy engine and Segregation of Duties (workstream 7a).

Tests policy evaluation, condition matching, and SoD enforcement.
"""

from __future__ import annotations

from rulerepo_server.core.abac import ABACEngine
from rulerepo_server.core.sod import SoDViolation, check_segregation_of_duties
from rulerepo_server.domain.abac import (
    ABACPolicy,
    PolicyCondition,
    PolicyEffect,
)

# ---------------------------------------------------------------------------
# ABAC domain tests
# ---------------------------------------------------------------------------


class TestABACDomain:
    def test_policy_effect_values(self) -> None:
        assert PolicyEffect.ALLOW == "ALLOW"
        assert PolicyEffect.DENY == "DENY"

    def test_policy_condition(self) -> None:
        cond = PolicyCondition(attribute="principal.role", operator="in", value=["admin", "auditor"])
        assert cond.operator == "in"
        assert "admin" in cond.value

    def test_policy_creation(self) -> None:
        policy = ABACPolicy(
            id="pol_001",
            name="HR read access",
            effect=PolicyEffect.ALLOW,
            conditions=[
                PolicyCondition(attribute="principal.department", operator="eq", value="hr"),
            ],
            resource_type="rule",
            actions=["read"],
            priority=10,
            description="HR can read HR rules",
        )
        assert policy.priority == 10
        assert len(policy.actions) == 1


# ---------------------------------------------------------------------------
# ABAC engine tests
# ---------------------------------------------------------------------------


class TestABACEngine:
    def _make_principal_attrs(self, **kwargs) -> dict:
        defaults = {
            "id": "u_001",
            "tenant_id": "t_001",
            "department_ids": [],
            "clearance": "internal",
            "roles": [],
        }
        defaults.update(kwargs)
        return defaults

    def test_empty_engine_denies(self) -> None:
        engine = ABACEngine()
        decision = engine.evaluate(
            self._make_principal_attrs(),
            "rule",
            "read",
            {},
        )
        assert decision.effect == PolicyEffect.DENY

    def test_matching_allow_policy(self) -> None:
        engine = ABACEngine()
        engine.load_policies(
            [
                ABACPolicy(
                    id="p1",
                    name="Allow all reads",
                    effect=PolicyEffect.ALLOW,
                    conditions=[],
                    resource_type="rule",
                    actions=["read"],
                    priority=1,
                    description="",
                ),
            ]
        )
        decision = engine.evaluate(
            self._make_principal_attrs(),
            "rule",
            "read",
            {},
        )
        assert decision.effect == PolicyEffect.ALLOW

    def test_deny_overrides_allow_by_priority(self) -> None:
        engine = ABACEngine()
        engine.load_policies(
            [
                ABACPolicy(
                    id="p1",
                    name="Allow",
                    effect=PolicyEffect.ALLOW,
                    conditions=[],
                    resource_type="rule",
                    actions=["read"],
                    priority=1,
                    description="",
                ),
                ABACPolicy(
                    id="p2",
                    name="Deny restricted",
                    effect=PolicyEffect.DENY,
                    conditions=[
                        PolicyCondition(attribute="resource.classification", operator="eq", value="restricted"),
                    ],
                    resource_type="rule",
                    actions=["read"],
                    priority=100,
                    description="",
                ),
            ]
        )
        decision = engine.evaluate(
            self._make_principal_attrs(),
            "rule",
            "read",
            {"classification": "restricted"},
        )
        assert decision.effect == PolicyEffect.DENY

    def test_action_mismatch_skips_policy(self) -> None:
        engine = ABACEngine()
        engine.load_policies(
            [
                ABACPolicy(
                    id="p1",
                    name="Allow writes",
                    effect=PolicyEffect.ALLOW,
                    conditions=[],
                    resource_type="rule",
                    actions=["write"],
                    priority=1,
                    description="",
                ),
            ]
        )
        decision = engine.evaluate(
            self._make_principal_attrs(),
            "rule",
            "read",
            {},
        )
        assert decision.effect == PolicyEffect.DENY

    def test_resource_type_mismatch(self) -> None:
        engine = ABACEngine()
        engine.load_policies(
            [
                ABACPolicy(
                    id="p1",
                    name="Allow rule read",
                    effect=PolicyEffect.ALLOW,
                    conditions=[],
                    resource_type="rule",
                    actions=["read"],
                    priority=1,
                    description="",
                ),
            ]
        )
        decision = engine.evaluate(
            self._make_principal_attrs(),
            "evaluation",
            "read",
            {},
        )
        assert decision.effect == PolicyEffect.DENY


# ---------------------------------------------------------------------------
# Segregation of Duties tests
# ---------------------------------------------------------------------------


class TestSegregationOfDuties:
    def test_proposer_cannot_approve_own(self) -> None:
        violation = check_segregation_of_duties(
            actor_id="user_1",
            action="approve",
            resource_id="proposal_1",
            history=[
                {"actor_id": "user_1", "action": "propose", "resource_id": "proposal_1"},
            ],
        )
        assert violation is not None

    def test_different_user_can_approve(self) -> None:
        violation = check_segregation_of_duties(
            actor_id="user_2",
            action="approve",
            resource_id="proposal_1",
            history=[
                {"actor_id": "user_1", "action": "propose", "resource_id": "proposal_1"},
            ],
        )
        assert violation is None

    def test_approver_cannot_enact(self) -> None:
        violation = check_segregation_of_duties(
            actor_id="user_1",
            action="enact",
            resource_id="proposal_1",
            history=[
                {"actor_id": "user_2", "action": "propose", "resource_id": "proposal_1"},
                {"actor_id": "user_1", "action": "approve", "resource_id": "proposal_1"},
            ],
        )
        assert violation is not None

    def test_no_history_no_violation(self) -> None:
        violation = check_segregation_of_duties(
            actor_id="user_1",
            action="propose",
            resource_id="proposal_1",
            history=[],
        )
        assert violation is None

    def test_sod_violation_fields(self) -> None:
        v = SoDViolation(
            rule_name="proposer_not_approver",
            actor="user_1",
            conflicting_action="approve",
            description="Proposer cannot approve their own proposal",
        )
        assert v.rule_name == "proposer_not_approver"
        assert v.actor == "user_1"
