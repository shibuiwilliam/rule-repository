"""EvaluationSubject abstraction per PROJECT.md §6.6.

The evaluation engine accepts any EvaluationSubject kind. Each kind has a
dedicated context assembler, rule selector strategy, and evaluation prompt set.
Code change is one variant among many, not the default.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


class EvaluationSubjectKind(str, enum.Enum):
    """Discriminator for the polymorphic EvaluationSubject."""

    CODE_CHANGE = "code_change"
    BUSINESS_EVENT = "business_event"
    DOCUMENT_ARTIFACT = "document_artifact"
    TRANSACTION = "transaction"
    COMMUNICATION = "communication"
    DECISION_REQUEST = "decision_request"


@dataclass(frozen=True)
class EvaluationSubject:
    """Abstract base for all evaluation subjects.

    Each concrete variant adds kind-specific fields.  The ``kind`` field
    is the discriminator for dispatch.
    """

    kind: EvaluationSubjectKind
    actor_id: str | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CodeChangeSubject(EvaluationSubject):
    """A unified diff or set of file changes.

    Consumers: CI pipelines, AI coding agents, PR review.
    """

    diff: str = ""
    files: list[dict[str, Any]] = field(default_factory=list)
    repository: str | None = None

    def __post_init__(self) -> None:
        if self.kind != EvaluationSubjectKind.CODE_CHANGE:
            object.__setattr__(self, "kind", EvaluationSubjectKind.CODE_CHANGE)


@dataclass(frozen=True)
class BusinessEventSubject(EvaluationSubject):
    """A discrete event in a business workflow with a payload.

    Consumers: HR systems (overtime register), travel, attendance.
    """

    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind != EvaluationSubjectKind.BUSINESS_EVENT:
            object.__setattr__(self, "kind", EvaluationSubjectKind.BUSINESS_EVENT)


@dataclass(frozen=True)
class DocumentArtifactSubject(EvaluationSubject):
    """A document or document section under review.

    Consumers: contract management, marketing asset review, policy authoring.
    """

    document_id: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    intent: str = ""  # "draft_review", "publish_check", etc.

    def __post_init__(self) -> None:
        if self.kind != EvaluationSubjectKind.DOCUMENT_ARTIFACT:
            object.__setattr__(self, "kind", EvaluationSubjectKind.DOCUMENT_ARTIFACT)


@dataclass(frozen=True)
class TransactionSubject(EvaluationSubject):
    """A financial or commercial transaction.

    Consumers: expense systems, ERP, procurement, payment systems.
    """

    transaction_type: str = ""  # "expense", "purchase_order", "wire_transfer"
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    counterparties: list[str] = field(default_factory=list)
    line_items: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind != EvaluationSubjectKind.TRANSACTION:
            object.__setattr__(self, "kind", EvaluationSubjectKind.TRANSACTION)


@dataclass(frozen=True)
class CommunicationSubject(EvaluationSubject):
    """An outbound message or public artifact.

    Consumers: email gateways, social media tools, internal chat moderation.
    """

    channel: str = ""  # "email", "slack", "twitter"
    sender_id: str = ""
    recipient_ids: list[str] = field(default_factory=list)
    content: str = ""
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind != EvaluationSubjectKind.COMMUNICATION:
            object.__setattr__(self, "kind", EvaluationSubjectKind.COMMUNICATION)


@dataclass(frozen=True)
class DecisionRequestSubject(EvaluationSubject):
    """A generic approval request.

    Consumers: workflow systems, approval queues.
    """

    request_type: str = ""
    description: str = ""
    options: list[str] = field(default_factory=list)
    context_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind != EvaluationSubjectKind.DECISION_REQUEST:
            object.__setattr__(self, "kind", EvaluationSubjectKind.DECISION_REQUEST)


# Mapping from kind to concrete class
SUBJECT_CLASSES: dict[EvaluationSubjectKind, type[EvaluationSubject]] = {
    EvaluationSubjectKind.CODE_CHANGE: CodeChangeSubject,
    EvaluationSubjectKind.BUSINESS_EVENT: BusinessEventSubject,
    EvaluationSubjectKind.DOCUMENT_ARTIFACT: DocumentArtifactSubject,
    EvaluationSubjectKind.TRANSACTION: TransactionSubject,
    EvaluationSubjectKind.COMMUNICATION: CommunicationSubject,
    EvaluationSubjectKind.DECISION_REQUEST: DecisionRequestSubject,
}
