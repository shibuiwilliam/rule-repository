"""Domain types for classification-based access control.

Pure domain -- no imports from services/, adapters/, or api/.

Classification levels control visibility of rules, evaluations, and audit entries.
See CLAUDE.md section 14 and ADR 0003.
"""

from __future__ import annotations

from enum import StrEnum


class Classification(StrEnum):
    """Data classification level, ordered from least to most restrictive.

    - PUBLIC: visible to all authenticated users within the tenant.
    - INTERNAL: visible to any org member.
    - CONFIDENTIAL: visible to department members + approved subscribers.
    - RESTRICTED: visible to named individuals or AUDITORs only.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# Numeric ranking for comparison (higher = more restrictive).
_CLASSIFICATION_RANK: dict[Classification, int] = {
    Classification.PUBLIC: 0,
    Classification.INTERNAL: 1,
    Classification.CONFIDENTIAL: 2,
    Classification.RESTRICTED: 3,
}


def classification_rank(cls: Classification) -> int:
    """Return numeric rank for classification comparison (higher = more restrictive)."""
    return _CLASSIFICATION_RANK.get(cls, 0)


def clearance_sufficient(user_clearance: Classification, required: Classification) -> bool:
    """Check whether a user's clearance is high enough for the required classification.

    Args:
        user_clearance: The user's maximum clearance level.
        required: The classification level of the resource.

    Returns:
        True if the user's clearance is >= the required classification.
    """
    return classification_rank(user_clearance) >= classification_rank(required)
