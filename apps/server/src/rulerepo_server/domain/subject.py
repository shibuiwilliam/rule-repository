"""Domain models for business event subjects.

Per CLAUDE.md Tier 2: Subject represents the entity or person involved
in a business event. SubjectFilter enables partial matching for rule
applicability.
"""

from __future__ import annotations

from dataclasses import dataclass


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
