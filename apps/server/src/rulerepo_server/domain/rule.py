"""Core domain model for rules — the central first-class entity.

This module contains only pure Python types with no external dependencies.
The Rule and its value objects represent the domain as described in PROJECT.md §5.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

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

    # Provenance
    source_refs: list[SourceRef] = field(default_factory=list)

    # Scope & applicability
    scope: list[str] = field(default_factory=list)
    effective_period: EffectivePeriod = field(default_factory=EffectivePeriod)
    preconditions: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)

    # Metadata
    rationale: str = ""
    tags: list[str] = field(default_factory=list)
    governance: Governance = field(default_factory=lambda: Governance(owner="system"))

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
