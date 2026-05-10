"""REST API router for universal business event ingestion.

See PROJECT.md §6.11 and CLAUDE.md §14.8.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.business_event import ActorRef, BusinessEvent
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class EventActorPayload(BaseModel):
    """Actor reference in the event payload."""

    type: Literal["employee", "system", "agent"]
    id: str
    department: str | None = None


class EventSubjectPayload(BaseModel):
    """Subject embedded in the event payload."""

    type: str = Field(..., description="Subject kind (e.g., 'transaction', 'document')")
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    context_facts: dict[str, Any] = Field(default_factory=dict)


class IngestEventRequest(BaseModel):
    """Request body for POST /api/v1/events/ingest."""

    event_type: str = Field(..., description="Dot-separated event name", examples=["finance.expense.submitted"])
    actor: EventActorPayload
    subject: EventSubjectPayload
    occurred_at: datetime
    correlation_id: str = Field(..., description="Business system's own ID")
    mode: Literal["preflight", "posthoc", "sidecar"] = "preflight"


class IngestEventResponse(BaseModel):
    """Response from event ingestion."""

    correlation_id: str
    verdict: str
    rules_evaluated: int
    violations: int
    evaluation_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _to_subject_kind(type_str: str) -> SubjectKind:
    """Map a subject type string to SubjectKind."""
    mapping: dict[str, SubjectKind] = {
        "transaction": SubjectKind.TRANSACTION,
        "document": SubjectKind.DOCUMENT,
        "document_draft": SubjectKind.DOCUMENT,
        "code_change": SubjectKind.CODE_DIFF,
        "code_diff": SubjectKind.CODE_DIFF,
        "communication": SubjectKind.CREATIVE,
        "event": SubjectKind.EVENT,
        "clause_set": SubjectKind.CLAUSE_SET,
    }
    return mapping.get(type_str, SubjectKind.EVENT)


@router.post("/ingest", response_model=IngestEventResponse)
async def ingest_event(
    body: IngestEventRequest,
    session: AsyncSession = Depends(get_db_session),
) -> IngestEventResponse:
    """Ingest a business event for evaluation.

    Business systems push events to this single endpoint. The handler
    resolves scope from ``event_type``, selects applicable rules, and
    dispatches to the correct subject evaluator.

    Returns synchronous verdict for ``preflight``/``posthoc`` modes,
    or 202 for ``sidecar`` mode.
    """
    subject = EvaluationSubject(
        kind=_to_subject_kind(body.subject.type),
        payload=body.subject.payload,
        context=body.subject.context_facts,
        metadata=body.subject.metadata,
    )

    actor = ActorRef(
        type=body.actor.type,
        id=body.actor.id,
        department=body.actor.department,
    )

    event = BusinessEvent(
        event_type=body.event_type,
        actor=actor,
        subject=subject,
        occurred_at=body.occurred_at,
        correlation_id=body.correlation_id,
        mode=body.mode,
    )

    from rulerepo_server.services.events.ingest import EventIngestionService

    svc = EventIngestionService(session)
    result = await svc.ingest(event)

    return IngestEventResponse(
        correlation_id=body.correlation_id,
        verdict=result.overall_verdict.value,
        rules_evaluated=result.rules_evaluated,
        violations=result.rules_violated,
        evaluation_id=result.evaluation_id,
    )
