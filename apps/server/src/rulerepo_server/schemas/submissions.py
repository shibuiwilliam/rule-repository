"""Pydantic schemas for the Universal Submissions API.

POST /api/v1/submissions accepts any EvaluationSubject kind via
a discriminated union on the ``kind`` field.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class SubjectBase(BaseModel):
    """Common fields for all evaluation subjects."""

    actor_id: str | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeChangeInput(SubjectBase):
    """Input for code change evaluation."""

    kind: Literal["code_change"] = "code_change"
    diff: str = ""
    files: list[dict[str, Any]] = Field(default_factory=list)
    repository: str | None = None


class BusinessEventInput(SubjectBase):
    """Input for business event evaluation."""

    kind: Literal["business_event"] = "business_event"
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DocumentArtifactInput(SubjectBase):
    """Input for document artifact evaluation."""

    kind: Literal["document_artifact"] = "document_artifact"
    document_id: str = ""
    sections: list[dict[str, Any]] = Field(default_factory=list)
    intent: str = ""


class TransactionInput(SubjectBase):
    """Input for transaction evaluation."""

    kind: Literal["transaction"] = "transaction"
    transaction_type: str
    amount: Decimal
    currency: str = "USD"
    counterparties: list[str] = Field(default_factory=list)
    line_items: list[dict[str, Any]] = Field(default_factory=list)


class CommunicationInput(SubjectBase):
    """Input for communication evaluation."""

    kind: Literal["communication"] = "communication"
    channel: str
    sender_id: str = ""
    recipient_ids: list[str] = Field(default_factory=list)
    content: str = ""
    attachments: list[str] = Field(default_factory=list)


class DecisionRequestInput(SubjectBase):
    """Input for decision request evaluation."""

    kind: Literal["decision_request"] = "decision_request"
    request_type: str
    description: str = ""
    options: list[str] = Field(default_factory=list)
    context_data: dict[str, Any] = Field(default_factory=dict)


# Discriminated union
SubjectInput = (
    CodeChangeInput
    | BusinessEventInput
    | DocumentArtifactInput
    | TransactionInput
    | CommunicationInput
    | DecisionRequestInput
)


class ScopeInput(BaseModel):
    """Structured scope for submission."""

    domain: str | None = None
    org_unit: str | None = None
    subject_type: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class UniversalSubmissionRequest(BaseModel):
    """Request body for POST /api/v1/submissions."""

    subject: SubjectInput = Field(..., discriminator="kind")
    scope: ScopeInput | None = None
    intent: str | None = None
    mode: Literal["preflight", "posthoc", "sidecar"] = "preflight"
    submission_id: str | None = Field(
        default=None,
        description="Optional idempotency key. Same ID returns same verdict within a window.",
    )


class ViolationResponse(BaseModel):
    """A single rule violation in the submission response."""

    rule_id: str
    statement: str
    reason: str
    severity: str = "MEDIUM"
    remediations: list[str] = Field(default_factory=list)


class SubmissionResponse(BaseModel):
    """Response body for POST /api/v1/submissions."""

    verdict: str  # "ALLOW", "DENY", "NEEDS_CONFIRMATION"
    violations: list[ViolationResponse] = Field(default_factory=list)
    applied_rules: list[str] = Field(default_factory=list)
    deterministic_results: list[dict[str, Any]] = Field(default_factory=list)
    llm_results: list[dict[str, Any]] = Field(default_factory=list)
    suggested_fix: str | None = None
    submission_id: str | None = None
