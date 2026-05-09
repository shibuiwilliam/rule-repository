"""Domain layer — pure business objects with no external dependencies."""

from rulerepo_server.domain.audit import GENESIS_HASH, AuditEntry
from rulerepo_server.domain.evaluation import Actor, Surface
from rulerepo_server.domain.revision import RuleRevision
from rulerepo_server.domain.rule import (
    VALID_STATUS_TRANSITIONS,
    EffectivePeriod,
    Governance,
    Modality,
    NormTier,
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
    "Actor",
    "AuditEntry",
    "EffectivePeriod",
    "Governance",
    "Modality",
    "NormTier",
    "RelationshipType",
    "Rule",
    "RuleRelationship",
    "RuleRevision",
    "RuleStatus",
    "Severity",
    "SourceRef",
    "Surface",
    "Verdict",
    "VerdictType",
    "validate_status_transition",
]
