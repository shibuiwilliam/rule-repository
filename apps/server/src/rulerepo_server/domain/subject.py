"""Domain models for evaluation subjects.

Subject represents the entity or person involved in a business event.
SubjectFilter enables partial matching for rule applicability.
SubjectType and EvaluationSubject support the Phase 7b subject abstraction.

See: IMPROVEMENT.md Phase 7b, CLAUDE.md §14
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class SubjectType(str, enum.Enum):
    """Type of entity being evaluated against rules.

    Each type has a corresponding adapter that knows how to parse
    the payload, assemble context, and format prompts.
    """

    CODE_CHANGE = "code_change"
    HR_EVENT = "hr_event"
    CONTRACT_CLAUSE = "contract_clause"
    EXPENSE_CLAIM = "expense_claim"
    MARKETING_COPY = "marketing_copy"
    VENDOR_ONBOARDING = "vendor_onboarding"
    DOCUMENT_REVISION = "document_revision"
    TRANSACTION = "transaction"
    CUSTOM = "custom"


class LegalForce(str, enum.Enum):
    """Legal authority level of a rule."""

    STATUTORY = "statutory"
    REGULATORY = "regulatory"
    CONTRACTUAL = "contractual"
    POLICY = "policy"
    GUIDELINE = "guideline"


@dataclass
class EvaluationSubject:
    """The entity being evaluated against rules — Phase 7b subject envelope.

    Wraps a typed payload with metadata. The evaluation pipeline uses the
    ``type`` field to dispatch to the correct adapter.

    Attributes:
        type: The subject type (determines adapter routing).
        payload: Type-specific data (diff for code_change, event details
            for hr_event, clause text for contract_clause, etc.).
        context: Additional context.
        metadata: Freeform metadata (actor, timestamp, source system).
    """

    type: SubjectType
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy_diff(cls, diff: str, **kwargs: Any) -> EvaluationSubject:
        """Create a code_change EvaluationSubject from a legacy diff request.

        Backward-compatibility shim: existing callers that send a raw diff
        are wrapped in an EvaluationSubject transparently.
        """
        return cls(
            type=SubjectType.CODE_CHANGE,
            payload={"diff": diff, **{k: v for k, v in kwargs.items() if k != "diff"}},
        )


@dataclass(frozen=True)
class Subject:
    """Represents the entity or person involved in a business event.

    Attributes:
        organization_unit: Organizational unit (e.g., "sales", "engineering").
        role: Job role or title (e.g., "manager", "engineer").
        employment_type: Type of employment (e.g., "full-time", "contract").
        location: Geographic location (e.g., "tokyo", "us-west").
        seniority_level: Numeric seniority level (e.g., 1-10).
        department: Department name (e.g., "hr", "finance").
    """

    organization_unit: str | None = None
    role: str | None = None
    employment_type: str | None = None
    location: str | None = None
    seniority_level: int | None = None
    department: str | None = None


@dataclass(frozen=True)
class SubjectFilter:
    """Partial Subject for matching. All non-None fields must match.

    Used in rule applicability checks: a rule with a SubjectFilter
    applies to a Subject only if every non-None field in the filter
    matches the corresponding field in the Subject.

    Attributes:
        organization_unit: Required org unit, or None to skip check.
        role: Required role, or None to skip check.
        employment_type: Required employment type, or None to skip check.
        location: Required location, or None to skip check.
        department: Required department, or None to skip check.
    """

    organization_unit: str | None = None
    role: str | None = None
    employment_type: str | None = None
    location: str | None = None
    department: str | None = None

    def matches(self, subject: Subject) -> bool:
        """Check if this filter matches the given subject.

        All non-None fields in the filter must match the corresponding
        field in the subject. Comparison is case-insensitive.

        Args:
            subject: The Subject to match against.

        Returns:
            True if all non-None filter fields match.
        """
        if self.organization_unit is not None:
            if subject.organization_unit is None:
                return False
            if self.organization_unit.lower() != subject.organization_unit.lower():
                return False

        if self.role is not None:
            if subject.role is None:
                return False
            if self.role.lower() != subject.role.lower():
                return False

        if self.employment_type is not None:
            if subject.employment_type is None:
                return False
            if self.employment_type.lower() != subject.employment_type.lower():
                return False

        if self.location is not None:
            if subject.location is None:
                return False
            if self.location.lower() != subject.location.lower():
                return False

        if self.department is not None:
            if subject.department is None:
                return False
            if self.department.lower() != subject.department.lower():
                return False

        return True
