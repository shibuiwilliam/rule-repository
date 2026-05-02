"""Domain model for governance proposals — rule change lifecycle management.

Proposals wrap rule changes (create, amend, retire, merge, split, override) in a
reviewable workflow with threaded comments, approval votes, and automated analysis.
See PROJECT_ENHANCE.md §Enhancement 1.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC

_UTC = UTC


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProposalType(str, enum.Enum):
    """The kind of change a proposal represents."""

    CREATE = "create"
    AMEND = "amend"
    RETIRE = "retire"
    MERGE = "merge"
    SPLIT = "split"
    OVERRIDE = "override"


class ProposalStatus(str, enum.Enum):
    """Lifecycle status of a governance proposal."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ENACTED = "enacted"
    REVERTED = "reverted"
    CLOSED = "closed"


class CommentType(str, enum.Enum):
    """Type of comment on a proposal."""

    COMMENT = "comment"
    SUGGESTION = "suggestion"
    RESOLUTION = "resolution"


class NotificationType(str, enum.Enum):
    """Type of notification event."""

    REVIEW_REQUESTED = "review_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONFLICT_DETECTED = "conflict_detected"
    COMMENT_ADDED = "comment_added"
    ENACTED = "enacted"
    REVERTED = "reverted"


# ---------------------------------------------------------------------------
# Status transition validation
# ---------------------------------------------------------------------------


VALID_PROPOSAL_TRANSITIONS: dict[ProposalStatus, list[ProposalStatus]] = {
    ProposalStatus.DRAFT: [ProposalStatus.REVIEW, ProposalStatus.CLOSED],
    ProposalStatus.REVIEW: [ProposalStatus.APPROVED, ProposalStatus.REJECTED, ProposalStatus.DRAFT],
    ProposalStatus.APPROVED: [ProposalStatus.ENACTED, ProposalStatus.CLOSED],
    ProposalStatus.REJECTED: [ProposalStatus.DRAFT, ProposalStatus.CLOSED],
    ProposalStatus.ENACTED: [ProposalStatus.REVERTED],
    ProposalStatus.REVERTED: [ProposalStatus.CLOSED],
    ProposalStatus.CLOSED: [],  # terminal
}


def validate_proposal_transition(current: ProposalStatus, target: ProposalStatus) -> None:
    """Validate that a proposal status transition is allowed.

    Args:
        current: The proposal's current status.
        target: The desired new status.

    Raises:
        ValueError: If the transition is not permitted.
    """
    if current == target:
        return
    allowed = VALID_PROPOSAL_TRANSITIONS.get(current, [])
    if target not in allowed:
        allowed_names = [s.value for s in allowed] if allowed else ["(none — terminal)"]
        msg = f"Invalid proposal transition: {current.value} → {target.value}. Allowed: {', '.join(allowed_names)}"
        raise ValueError(msg)


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApprovalVote:
    """A single vote on a proposal."""

    user_id: str
    vote: str  # approve, reject, conditional
    condition: str | None = None
    timestamp: str = ""


@dataclass(frozen=True)
class ChangeSpec:
    """Structured diff of proposed rule changes."""

    fields_changed: dict[str, dict[str, object]] = field(default_factory=dict)
    new_rule_data: dict[str, object] | None = None
    merge_source_ids: list[str] | None = None
    split_targets: list[dict[str, object]] | None = None
