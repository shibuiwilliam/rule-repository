"""Domain models for evaluation subjects.

SubjectKind is the discriminator for the polymorphic Subject protocol.
Each subject kind has a corresponding adapter that knows how to parse
the payload, assemble context, and format prompts.

Subject (frozen dataclass) represents the entity or person involved in
a business event. SubjectFilter enables partial matching for rule
applicability.

See: PROJECT.md §5.2, CLAUDE.md §11
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class SubjectKind(str, enum.Enum):
    """Type of entity being evaluated against rules.

    Each kind has a corresponding adapter registered via
    ``@register(SubjectKind.X)`` in ``subjects/registry.py``.
    """

    CODE_DIFF = "code_diff"
    CLAUSE_SET = "clause_set"
    EVENT = "event"
    TRANSACTION = "transaction"
    CREATIVE = "creative"
    DECISION = "decision"
    IDENTITY = "identity"
    DOCUMENT = "document"


# Backward-compatible alias for code that still imports the old name.
SubjectType = SubjectKind

# All subject kind values as a list of strings.
# Used as the permissive default when a rule has no explicit
# applicable_subject_types — such rules are considered universal.
ALL_SUBJECT_TYPES: list[str] = [kind.value for kind in SubjectKind]


class LegalForce(str, enum.Enum):
    """Legal authority level of a rule."""

    STATUTORY = "statutory"
    REGULATORY = "regulatory"
    CONTRACTUAL = "contractual"
    POLICY = "policy"
    GUIDELINE = "guideline"


class PromptFormat(str, enum.Enum):
    """Format hint for Subject.render_for_llm()."""

    FULL = "full"
    COMPACT = "compact"


@dataclass(frozen=True)
class Attachment:
    """Binary or referenced evidence attached to a subject.

    Attributes:
        name: Human-readable filename or label.
        mime_type: MIME type (e.g., "application/pdf").
        data: Raw bytes (for inline attachments) or None.
        uri: External URI (for referenced attachments) or None.
    """

    name: str
    mime_type: str
    data: bytes | None = None
    uri: str | None = None


@runtime_checkable
class SubjectAdapter(Protocol):
    """Protocol that every subject-kind adapter must implement.

    Each adapter translates a domain-specific payload into the uniform
    interface consumed by the evaluation pipeline.

    See CLAUDE.md §11.1 for the full specification.
    """

    kind: SubjectKind

    @property
    def identifier(self) -> str:
        """Stable identity string for audit."""
        ...

    def render_for_llm(self, facts: dict[str, Any], format: PromptFormat = PromptFormat.FULL) -> str:
        """Produce the prompt-friendly representation of the subject.

        This is the seam at which domain knowledge enters the evaluation
        pipeline. The orchestrator calls this instead of building prompts.
        """
        ...

    def extract_features(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract domain-specific features for rule selection and scoring."""
        ...

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Determine applicable rule scopes from the payload."""
        ...

    def parse_remediation(self, raw: dict[str, Any]) -> Any | None:
        """Parse a raw LLM remediation dict into a domain-specific Remediation."""
        ...

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        """Return JSON paths into ``payload`` that contain PII."""
        ...


@dataclass
class EvaluationSubject:
    """The entity being evaluated against rules — subject envelope.

    Wraps a typed payload with metadata. The evaluation pipeline uses the
    ``kind`` field to dispatch to the correct adapter.

    Attributes:
        kind: The subject kind (determines adapter routing).
        payload: Kind-specific data (diff for code_diff, event details
            for event, clause text for clause_set, etc.).
        context: Additional context.
        metadata: Freeform metadata (actor, timestamp, source system).
        locale: ISO language tag for locale-aware rule selection.
        jurisdiction: Legal jurisdiction (JP, US, EU, ...).
    """

    kind: SubjectKind
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    locale: str | None = None
    jurisdiction: str | None = None

    # Backward-compatible alias
    @property
    def type(self) -> SubjectKind:
        return self.kind

    @classmethod
    def from_legacy_diff(cls, diff: str, **kwargs: Any) -> EvaluationSubject:
        """Create a code_diff EvaluationSubject from a legacy diff request.

        Backward-compatibility shim: existing callers that send a raw diff
        are wrapped in an EvaluationSubject transparently.
        """
        return cls(
            kind=SubjectKind.CODE_DIFF,
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
