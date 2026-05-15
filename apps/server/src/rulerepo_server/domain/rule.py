"""Core domain model for rules — the central first-class entity.

This module contains only pure Python types with no external dependencies.
The Rule and its value objects represent the domain as described in PROJECT.md §5.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from rulerepo_server.domain.applies_to import AppliesTo
from rulerepo_server.domain.scope import StructuredScope

_UTC = UTC


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Modality(str, enum.Enum):
    """Strength of the normative obligation (RFC 2119-style)."""

    MUST = "MUST"
    MUST_NOT = "MUST_NOT"
    SHOULD = "SHOULD"
    MAY = "MAY"
    INFO = "INFO"


class Severity(str, enum.Enum):
    """Impact level when a rule is violated."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleStatus(str, enum.Enum):
    """Lifecycle status of a rule."""

    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    EFFECTIVE = "EFFECTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class MaturityLevel(str, enum.Enum):
    """Progressive enforcement level for rules (PROJECT_ENHANCE.md §2).

    experimental: shadow mode — DENY verdicts downgraded to NEEDS_CONFIRMATION.
    stable: warning mode — verdicts enforced, owner notified on DENY.
    proven: full enforcement — verdicts trusted, no notifications.
    """

    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    PROVEN = "proven"


class Sensitivity(str, enum.Enum):
    """Data classification level — drives LLM provider routing and log retention.

    PUBLIC: no restrictions.
    INTERNAL: standard handling, no special routing.
    CONFIDENTIAL: evaluation logs masked on frontend.
    RESTRICTED: routed to self-hosted LLM only; logs purge after 90 days.
    """

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class RegulatorySeverity(str, enum.Enum):
    """Regulatory penalty band — independent of operational Severity.

    NONE: no regulatory implications.
    GUIDANCE: administrative guidance, no penalty.
    FINE: monetary penalty risk.
    CRIMINAL: criminal liability risk.
    """

    NONE = "NONE"
    GUIDANCE = "GUIDANCE"
    FINE = "FINE"
    CRIMINAL = "CRIMINAL"


class RuleKind(str, enum.Enum):
    """Kind of rule — determines the evaluation strategy.

    Different kinds require fundamentally different evaluation approaches:
    - NORMATIVE: standard LLM-as-Judge (current behavior).
    - COMPUTATIONAL: deterministic calculation + LLM verification for edge cases.
    - PROCEDURAL: state-transition / ordering-constraint verification.
    - DEFINITIONAL: reference/lookup — definitions don't produce violations.
    - PRINCIPLE: high-level intent, evaluated through derived normative rules.

    See IMPROVEMENT.md Proposal 3.
    """

    NORMATIVE = "normative"
    COMPUTATIONAL = "computational"
    PROCEDURAL = "procedural"
    DEFINITIONAL = "definitional"
    PRINCIPLE = "principle"


# ---------------------------------------------------------------------------
# Rule Body Variants (per PROJECT.md §6.3 / CLAUDE.md §14.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormativeBody:
    """Body for normative rules — evaluated by LLM judge."""

    predicate: str | None = None  # Optional numeric/schema predicate for partial deterministic check


@dataclass(frozen=True)
class ComputationalBody:
    """Body for computational rules — evaluated by sandboxed expression engine.

    The expression is evaluated deterministically via asteval.
    The LLM only checks whether exception_predicate applies.
    """

    expression: str = ""
    required_inputs: list[str] = field(default_factory=list)
    unit: str | None = None
    exception_predicate: str | None = None


@dataclass(frozen=True)
class ProceduralBody:
    """Body for procedural rules — evaluated by state machine validator."""

    states: list[str] = field(default_factory=list)
    transitions: list[dict[str, str]] = field(default_factory=list)
    initial_state: str = ""
    terminal_states: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DefinitionalBody:
    """Body for definitional rules — evaluated by reference lookup + LLM."""

    term: str = ""
    definition: str = ""
    lookup_table: str | None = None  # Reference to a lookup table name


@dataclass(frozen=True)
class PrincipleBody:
    """Body for principle-level rules — evaluated by LLM with high context."""

    guidance: str = ""
    derived_rule_ids: list[str] = field(default_factory=list)


# Type alias for the discriminated body union
RuleBody = NormativeBody | ComputationalBody | ProceduralBody | DefinitionalBody | PrincipleBody


class NormTier(str, enum.Enum):
    """Position of a rule in the norm-lineage hierarchy.

    Drives amendment propagation: when a LAW or REGULATION is amended,
    all transitive downstream rules are flagged for review.
    See PROJECT.md §5.3 and CLAUDE.md §14.2.1.
    """

    LAW = "LAW"
    REGULATION = "REGULATION"
    GUIDELINE = "GUIDELINE"
    CORPORATE_POLICY = "CORPORATE_POLICY"
    DEPARTMENT_RULE = "DEPARTMENT_RULE"
    OPERATIONAL_RULE = "OPERATIONAL_RULE"


class RelationshipType(str, enum.Enum):
    """Types of relationships between rules (PROJECT.md §5.2)."""

    REFINES = "REFINES"
    OVERRIDES = "OVERRIDES"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVES_FROM = "DERIVES_FROM"
    SUCCEEDS = "SUCCEEDS"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectivePeriod:
    """Time window during which a rule is in effect."""

    valid_from: datetime | None = None
    valid_until: datetime | None = None


@dataclass(frozen=True)
class SourceRef:
    """Pointer to the source document from which a rule was extracted."""

    document_id: str
    section: str | None = None
    offset: int | None = None
    page: int | None = None


@dataclass(frozen=True)
class Governance:
    """Ownership and approval metadata for a rule."""

    owner: str
    approvers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclass
class Rule:
    """The central first-class entity — a natural-language normative statement.

    The `statement` field is the source of truth.  Structured fields exist
    for indexing, filtering, and prioritization — never to override the
    meaning of the statement.
    """

    # Identity
    id: UUID = field(default_factory=uuid4)

    # Core content
    statement: str = ""
    modality: Modality = Modality.MUST
    severity: Severity = Severity.MEDIUM
    status: RuleStatus = RuleStatus.DRAFT
    kind: RuleKind = RuleKind.NORMATIVE
    body: RuleBody = field(default_factory=NormativeBody)

    # Deterministic constraints (Proposal 9: Hybrid Evaluation Architecture)
    constraints: list[dict] = field(default_factory=list)

    # Provenance
    source_refs: list[SourceRef] = field(default_factory=list)

    # Scope & applicability
    scope: list[str] = field(default_factory=list)
    effective_period: EffectivePeriod = field(default_factory=EffectivePeriod)
    preconditions: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)

    # Metadata
    rationale: str = ""
    context: str = ""
    following_examples: list[str] = field(default_factory=list)
    violation_examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    regulatory_severity: RegulatorySeverity = RegulatorySeverity.NONE
    equivalence_id: str | None = None
    applicable_subject_types: list[str] = field(default_factory=lambda: ["code_diff"])
    applies_to: AppliesTo = field(default_factory=AppliesTo)
    structured_scope: StructuredScope = field(default_factory=StructuredScope)
    jurisdiction: str = "global"
    legal_force: str = "policy"
    review_cadence: str | None = None
    governance: Governance = field(default_factory=lambda: Governance(owner="system"))

    # Multilingual (CLAUDE.md §14.8)
    language: str = "en"  # ISO 639-1

    # Phase 8 — Surface-aware fields (CLAUDE.md §14.2.1)
    applies_to_surfaces: list[str] = field(default_factory=lambda: ["generic"])
    norm_tier: NormTier = NormTier.OPERATIONAL_RULE
    norm_authority: str | None = None
    locale: str = "en"
    statement_translations: dict[str, str] = field(default_factory=dict)
    tech_scope: list[str] = field(default_factory=list)
    org_scope: list[str] = field(default_factory=list)

    # Derived
    embedding: list[float] = field(default_factory=list, repr=False)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))


# ---------------------------------------------------------------------------
# Status transition validation
# ---------------------------------------------------------------------------

VALID_STATUS_TRANSITIONS: dict[RuleStatus, list[RuleStatus]] = {
    RuleStatus.DRAFT: [RuleStatus.REVIEW, RuleStatus.RETIRED],
    RuleStatus.REVIEW: [RuleStatus.APPROVED, RuleStatus.DRAFT, RuleStatus.RETIRED],
    RuleStatus.APPROVED: [RuleStatus.EFFECTIVE, RuleStatus.REVIEW, RuleStatus.RETIRED],
    RuleStatus.EFFECTIVE: [RuleStatus.SUPERSEDED, RuleStatus.RETIRED],
    RuleStatus.SUPERSEDED: [RuleStatus.RETIRED],
    RuleStatus.RETIRED: [],  # terminal state — rules are never deleted
}


def validate_status_transition(current: RuleStatus, target: RuleStatus) -> None:
    """Validate that a status transition is allowed.

    Args:
        current: The rule's current status.
        target: The desired new status.

    Raises:
        ValueError: If the transition is not permitted.
    """
    if current == target:
        return
    allowed = VALID_STATUS_TRANSITIONS.get(current, [])
    if target not in allowed:
        allowed_names = [s.value for s in allowed] if allowed else ["(none — terminal)"]
        msg = (
            f"Invalid status transition: {current.value} → {target.value}. "
            f"Allowed transitions from {current.value}: {', '.join(allowed_names)}"
        )
        raise ValueError(msg)


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleRelationship:
    """A directed edge between two rules in the rule graph."""

    source_id: UUID
    target_id: UUID
    relationship_type: RelationshipType
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))
    created_by: str = "system"
