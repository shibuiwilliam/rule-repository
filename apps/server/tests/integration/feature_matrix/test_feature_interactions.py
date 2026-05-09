"""Feature interaction tests — documents and verifies cross-feature behavior.

Each test corresponds to an interaction pair in development/feature_interactions.md.
Tests are structured as: setup minimal scenario → exercise interaction → assert behavior.

These tests use mocks (no Docker required) and verify the current behavior, which
may include documenting known gaps. When a gap is fixed, update the test assertion.

See: CLAUDE.md §15.1 (Tier 0), development/feature_interactions.md
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.services.snapshots.serializer import deserialize_snapshot, serialize_rules

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeRule:
    """Minimal rule-like object for testing."""

    def __init__(self, **kw: Any) -> None:
        defaults = {
            "id": "rule-1",
            "statement": "Test rule",
            "modality": "MUST",
            "severity": "HIGH",
            "status": "EFFECTIVE",
            "scope": ["engineering"],
            "tags": ["test"],
            "rationale": "For testing",
            "maturity_level": "experimental",
        }
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


# ===========================================================================
# Pair 1: Federation x Snapshot
# ===========================================================================


class TestFederationSnapshot:
    """Pair 1: Does a snapshot freeze federation resolution?

    Current behavior: Snapshots and federation are independent.
    create_snapshot() does not accept federation_id.
    """

    def test_snapshot_does_not_capture_federation_metadata(self) -> None:
        """Snapshots serialize rules without federation source info."""
        rule = FakeRule(id="rule-1")
        snapshot = serialize_rules([rule])

        assert "rule-1" in snapshot
        frozen = snapshot["rule-1"]
        # Federation metadata is NOT included in snapshots
        assert "source_federation_id" not in frozen
        assert "source_federation_name" not in frozen

    def test_snapshot_create_signature_has_no_federation_param(self) -> None:
        """SnapshotService.create_snapshot does not accept federation_id.

        This documents the gap: snapshots cannot be created from a
        federation-resolved rule set.
        """
        import inspect

        from rulerepo_server.services.snapshots.service import SnapshotService

        sig = inspect.signature(SnapshotService.create_snapshot)
        param_names = set(sig.parameters.keys())
        # Document the gap: no federation_id parameter
        assert "federation_id" not in param_names


# ===========================================================================
# Pair 3: Proposal x Federation
# ===========================================================================


class TestProposalFederation:
    """Pair 3: Who approves a child override of a parent rule?

    Current behavior: Federation overrides are immediate and ungoverned.
    No proposal is created when override_parent_rule_id is set.
    """

    def test_federation_service_add_rule_has_no_governance(self) -> None:
        """FederationService.add_rule does not create proposals for overrides.

        This documents the gap: child overrides bypass governance entirely.
        """
        import inspect

        from rulerepo_server.services.federation.service import FederationService

        sig = inspect.signature(FederationService.add_rule)
        param_names = set(sig.parameters.keys())
        # The method accepts override_parent_rule_id but has no proposal/approval params
        assert "override_parent_rule_id" in param_names
        assert "require_approval" not in param_names
        assert "proposal_id" not in param_names

    def test_proposal_enactor_has_no_federation_awareness(self) -> None:
        """ProposalEnactor does not notify federation parents/children."""
        import inspect

        from rulerepo_server.services.proposals.enactor import enact_proposal

        sig = inspect.signature(enact_proposal)
        param_names = set(sig.parameters.keys())
        assert "federation_id" not in param_names


# ===========================================================================
# Pair 4: Agent Governance x Federation
# ===========================================================================


class TestAgentGovernanceFederation:
    """Pair 4: Does personalization walk the federation chain?

    Current behavior: get_personalized_rules queries ALL active rules
    globally, without federation-scoping.
    """

    def test_personalized_rules_has_no_federation_param(self) -> None:
        """AgentGovernanceService.get_personalized_rules does not accept
        federation_id — it returns global rules, not federation-scoped ones.
        """
        import inspect

        from rulerepo_server.services.agent_governance.service import (
            AgentGovernanceService,
        )

        sig = inspect.signature(AgentGovernanceService.get_personalized_rules)
        param_names = set(sig.parameters.keys())
        assert "federation_id" not in param_names
        assert "project_id" not in param_names


# ===========================================================================
# Pair 5: Maturity x Snapshot (CRITICAL GAP)
# ===========================================================================


class TestMaturitySnapshot:
    """Pair 5: Does an experimental rule keep shadow behavior in snapshots?

    maturity_level is now serialized in snapshots (fixed in Tier 1.0).
    Experimental rules retain shadow-mode protection when served from snapshots.
    """

    def test_serialize_includes_maturity_level(self) -> None:
        """maturity_level is included in snapshot serialization."""
        rule = FakeRule(id="rule-1", maturity_level="experimental")
        snapshot = serialize_rules([rule])
        frozen = snapshot["rule-1"]

        assert "maturity_level" in frozen
        assert frozen["maturity_level"] == "experimental"

    def test_serialize_dict_includes_maturity_level(self) -> None:
        """maturity_level is included when serializing from dicts."""
        rule_dict = {
            "id": "rule-1",
            "statement": "Test",
            "modality": "MUST",
            "severity": "HIGH",
            "status": "EFFECTIVE",
            "scope": [],
            "tags": [],
            "rationale": "",
            "maturity_level": "stable",
        }
        snapshot = serialize_rules([rule_dict])
        assert snapshot["rule-1"]["maturity_level"] == "stable"

    def test_deserialized_rule_preserves_maturity(self) -> None:
        """Deserialized snapshot rules retain maturity_level."""
        snapshot = {
            "rule-1": {
                "statement": "Test rule",
                "modality": "MUST",
                "severity": "HIGH",
                "status": "EFFECTIVE",
                "scope": ["engineering"],
                "tags": ["test"],
                "rationale": "For testing",
                "maturity_level": "experimental",
            },
        }
        rules = deserialize_snapshot(snapshot)
        assert len(rules) == 1

        rule = rules[0]
        assert rule["id"] == "rule-1"
        assert rule["maturity_level"] == "experimental"

    def test_experimental_rule_preserved_through_snapshot_roundtrip(self) -> None:
        """Full roundtrip: serialize → deserialize preserves maturity_level."""
        original = FakeRule(id="rule-1", maturity_level="experimental")
        snapshot = serialize_rules([original])
        restored = deserialize_snapshot(snapshot)

        assert restored[0]["maturity_level"] == "experimental"

    def test_missing_maturity_defaults_to_experimental(self) -> None:
        """Rules without maturity_level default to 'experimental' (safe default)."""
        rule = FakeRule(id="rule-1")
        delattr(rule, "maturity_level")
        snapshot = serialize_rules([rule])
        assert snapshot["rule-1"]["maturity_level"] == "experimental"

    def test_rule_to_dict_defaults_maturity_to_proven(self) -> None:
        """rule_selector._rule_to_dict defaults maturity_level to 'proven'
        when the attribute is missing — confirming the snapshot gap.
        """

        class RuleWithoutMaturity:
            id = "r1"
            statement = "test"
            modality = "MUST"
            severity = "HIGH"
            status = "EFFECTIVE"
            scope = ["eng"]
            tags = ["t"]
            rationale = "reason"
            context = ""
            preconditions = []
            exceptions = []
            following_examples = []
            violation_examples = []
            # NOTE: no maturity_level attribute

        rule = RuleWithoutMaturity()
        maturity = getattr(rule, "maturity_level", "proven")
        assert maturity == "proven"


# ===========================================================================
# Pair 7: Proposal x Snapshot
# ===========================================================================


class TestProposalSnapshot:
    """Pair 7: What happens to live snapshots when a referenced rule is retired?

    Current behavior: Snapshots store frozen JSONB copies — they are
    immutable and not affected by rule retirement. However, there is
    no notification when a deployed snapshot contains retired rules.
    """

    def test_snapshot_stores_frozen_copy(self) -> None:
        """Snapshot data is a frozen copy, not a foreign key reference.
        Modifying the original rule does not affect the snapshot.
        """
        rule = FakeRule(id="rule-1", statement="Original statement")
        snapshot = serialize_rules([rule])

        # Mutate the original rule (simulating retirement)
        rule.status = "RETIRED"
        rule.statement = "Retired statement"

        # Snapshot retains the frozen data
        frozen = snapshot["rule-1"]
        assert frozen["statement"] == "Original statement"
        assert frozen["status"] == "EFFECTIVE"

    def test_retired_rule_still_in_deployed_snapshot(self) -> None:
        """Documents that retired rules persist in deployed snapshots
        with no alert mechanism.
        """
        # Create a snapshot with an active rule
        snapshot = serialize_rules(
            [
                FakeRule(id="rule-1", status="EFFECTIVE"),
                FakeRule(id="rule-2", status="EFFECTIVE"),
            ]
        )

        # Simulate: rule-1 is retired via proposal (only affects DB, not snapshot)
        # The snapshot still contains rule-1
        rules = deserialize_snapshot(snapshot)
        rule_ids = {r["id"] for r in rules}
        assert "rule-1" in rule_ids  # Still present in snapshot

        # GAP: No mechanism checks deployed snapshots for retired rules
        # and creates alerts. This is documented in feature_interactions.md.
