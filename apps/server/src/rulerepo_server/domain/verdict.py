"""Evaluation verdict types — placeholder for Phase 2 evaluation engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


class VerdictType(str, enum.Enum):
    """Result of evaluating an action against rules."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"
    REQUIRES_DISCLOSURE = "REQUIRES_DISCLOSURE"


@dataclass(frozen=True)
class Verdict:
    """The result of an evaluation, linking context, rules, and a judgment."""

    id: UUID = field(default_factory=uuid4)
    rule_ids: list[UUID] = field(default_factory=list)
    verdict: VerdictType = VerdictType.ALLOW
    reasoning: str = ""
    context_hash: str = ""
    model_id: str = ""
    prompt_version: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
