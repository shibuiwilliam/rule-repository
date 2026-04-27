"""Domain layer — pure business objects with no external dependencies."""

from rulerepo_server.domain.audit import GENESIS_HASH, AuditEntry
from rulerepo_server.domain.revision import RuleRevision
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
from rulerepo_server.domain.verdict import Verdict, VerdictType

__all__ = [
    "GENESIS_HASH",
    "VALID_STATUS_TRANSITIONS",
    "AuditEntry",
    "EffectivePeriod",
    "Governance",
    "Modality",
    "RelationshipType",
    "Rule",
    "RuleRelationship",
    "RuleRevision",
    "RuleStatus",
    "Severity",
    "SourceRef",
    "Verdict",
    "VerdictType",
    "validate_status_transition",
]
