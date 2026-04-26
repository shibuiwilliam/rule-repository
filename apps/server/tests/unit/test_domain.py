"""Unit tests for domain models — pure Python, no external deps."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from rulerepo_server.domain.audit import GENESIS_HASH, AuditEntry
from rulerepo_server.domain.rule import (
    VALID_STATUS_TRANSITIONS,
    EffectivePeriod,
    Governance,
    Modality,
    RelationshipType,
    Rule,
    RuleRelationship,
    RuleStatus,
    Severity,
    SourceRef,
    validate_status_transition,
)
from rulerepo_server.domain.revision import RuleRevision
from rulerepo_server.domain.verdict import Verdict, VerdictType


class TestModality:
    def test_values(self) -> None:
        assert Modality.MUST == "MUST"
        assert Modality.MUST_NOT == "MUST_NOT"
        assert Modality.SHOULD == "SHOULD"
        assert Modality.MAY == "MAY"
        assert Modality.INFO == "INFO"

    def test_from_string(self) -> None:
        assert Modality("MUST") == Modality.MUST


class TestSeverity:
    def test_ordering(self) -> None:
        values = [s.value for s in Severity]
        assert values == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class TestRuleStatus:
    def test_lifecycle(self) -> None:
        statuses = [s.value for s in RuleStatus]
        assert "DRAFT" in statuses
        assert "RETIRED" in statuses


class TestRelationshipType:
    def test_all_types(self) -> None:
        types = {t.value for t in RelationshipType}
        assert types == {
            "REFINES", "OVERRIDES", "CONFLICTS_WITH",
            "DEPENDS_ON", "DERIVES_FROM", "SUCCEEDS",
        }


class TestEffectivePeriod:
    def test_default(self) -> None:
        ep = EffectivePeriod()
        assert ep.valid_from is None
        assert ep.valid_until is None

    def test_with_dates(self) -> None:
        now = datetime.now(tz=timezone.utc)
        ep = EffectivePeriod(valid_from=now)
        assert ep.valid_from == now
        assert ep.valid_until is None


class TestSourceRef:
    def test_creation(self) -> None:
        ref = SourceRef(document_id="doc1", section="3.1", page=5)
        assert ref.document_id == "doc1"
        assert ref.section == "3.1"
        assert ref.page == 5


class TestRule:
    def test_default_creation(self) -> None:
        rule = Rule(statement="All code must have tests")
        assert isinstance(rule.id, UUID)
        assert rule.statement == "All code must have tests"
        assert rule.modality == Modality.MUST
        assert rule.severity == Severity.MEDIUM
        assert rule.status == RuleStatus.DRAFT
        assert rule.scope == []
        assert rule.tags == []

    def test_full_creation(self) -> None:
        rule = Rule(
            statement="Engineers must review PRs within 24 hours",
            modality=Modality.MUST,
            severity=Severity.HIGH,
            status=RuleStatus.EFFECTIVE,
            scope=["engineering"],
            tags=["code-review", "sla"],
            rationale="Ensures timely feedback",
            governance=Governance(owner="eng-lead", approvers=["cto"]),
        )
        assert rule.modality == Modality.MUST
        assert rule.severity == Severity.HIGH
        assert rule.governance.owner == "eng-lead"


class TestStatusTransitions:
    def test_valid_transitions(self) -> None:
        validate_status_transition(RuleStatus.DRAFT, RuleStatus.REVIEW)
        validate_status_transition(RuleStatus.REVIEW, RuleStatus.APPROVED)
        validate_status_transition(RuleStatus.APPROVED, RuleStatus.EFFECTIVE)
        validate_status_transition(RuleStatus.EFFECTIVE, RuleStatus.RETIRED)

    def test_same_status_is_noop(self) -> None:
        validate_status_transition(RuleStatus.DRAFT, RuleStatus.DRAFT)

    def test_invalid_transition_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_status_transition(RuleStatus.DRAFT, RuleStatus.EFFECTIVE)

    def test_retired_is_terminal(self) -> None:
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_status_transition(RuleStatus.RETIRED, RuleStatus.DRAFT)

    def test_all_statuses_have_transitions_defined(self) -> None:
        for status in RuleStatus:
            assert status in VALID_STATUS_TRANSITIONS


class TestRuleRelationship:
    def test_creation(self) -> None:
        from uuid import uuid4
        rel = RuleRelationship(
            source_id=uuid4(),
            target_id=uuid4(),
            relationship_type=RelationshipType.REFINES,
        )
        assert rel.relationship_type == RelationshipType.REFINES


class TestRuleRevision:
    def test_creation(self) -> None:
        rev = RuleRevision(
            statement="Updated rule text",
            modality="MUST",
            severity="HIGH",
            status="EFFECTIVE",
            revision_number=2,
            changed_by="eng-lead",
            change_note="Strengthened requirement",
        )
        assert rev.revision_number == 2
        assert rev.change_note == "Strengthened requirement"


class TestVerdict:
    def test_types(self) -> None:
        assert VerdictType.ALLOW == "ALLOW"
        assert VerdictType.DENY == "DENY"
        assert VerdictType.NEEDS_CONFIRMATION == "NEEDS_CONFIRMATION"

    def test_creation(self) -> None:
        verdict = Verdict(verdict=VerdictType.DENY, reasoning="Exceeds limit")
        assert verdict.verdict == VerdictType.DENY


class TestAuditEntry:
    def test_compute_hash(self) -> None:
        entry_data = {"action": "test", "actor": "system"}
        hash1 = AuditEntry.compute_hash(GENESIS_HASH, entry_data)
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_hash_chain(self) -> None:
        data1 = {"action": "create", "id": "1"}
        data2 = {"action": "update", "id": "2"}

        hash1 = AuditEntry.compute_hash(GENESIS_HASH, data1)
        hash2 = AuditEntry.compute_hash(hash1, data2)

        # Different entries produce different hashes
        assert hash1 != hash2

        # Same inputs produce same hash (deterministic)
        assert AuditEntry.compute_hash(GENESIS_HASH, data1) == hash1

    def test_genesis_hash(self) -> None:
        assert GENESIS_HASH == "0" * 64
