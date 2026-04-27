"""Rule revision tracking — immutable snapshots of rule state at each change."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class RuleRevision:
    """An immutable snapshot of a rule at a specific point in time.

    Created every time a rule is updated, preserving full history.
    """

    id: UUID = field(default_factory=uuid4)
    rule_id: UUID = field(default_factory=uuid4)
    revision_number: int = 1

    # Snapshot of mutable fields at the time of revision
    statement: str = ""
    modality: str = ""
    severity: str = ""
    status: str = ""
    scope: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    rationale: str = ""

    # Change metadata
    changed_by: str = "system"
    change_note: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
