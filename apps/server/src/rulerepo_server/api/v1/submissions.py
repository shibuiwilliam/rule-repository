"""REST API router for unified submission evaluation.

``POST /api/v1/submissions`` is the single entry point for any business event
or artifact that needs rule evaluation — code diffs, expense transactions,
contract clauses, HR events, sales communications, etc.

It combines the scope resolution of ``/events/ingest`` with the rich response
of ``/evaluate``, providing a subject-kind-polymorphic API that all business
systems can target.

See IMPROVEMENT.md §3 Proposal 7, CLAUDE.md §7.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.api.v1.evaluation import _result_to_response
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.evaluation import EvaluateResponse
from rulerepo_server.services.evaluation.service import EvaluationService
from rulerepo_server.services.events.scope_resolver import EventScopeResolver

logger = get_logger(__name__)

router = APIRouter(prefix="/submissions", tags=["submissions"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SubmissionActor(BaseModel):
    """Who is submitting the event or artifact for evaluation.

    Attributes:
        id: Stable actor identifier (employee ID, system name, agent ID).
        type: Actor category.
        department: Department the actor belongs to (used for scope resolution).
        role: Job role or title (optional, used for subject filtering).
        org_unit: Organizational unit (optional, for multi-level orgs).
    """

    id: str = Field(..., examples=["E001", "system:payroll", "agent:claude-code"])
    type: Literal["employee", "system", "agent"] = "employee"
    department: str | None = Field(default=None, examples=["finance", "hr", "legal", "engineering"])
    role: str | None = Field(default=None, examples=["manager", "clerk", "engineer"])
    org_unit: str | None = Field(default=None, examples=["tokyo-branch", "us-west"])


class SubmissionRequest(BaseModel):
    """Unified request body for ``POST /api/v1/submissions``.

    Accepts any subject kind with a polymorphic payload. The handler
    resolves scope from ``event_type`` and the actor's department,
    selects applicable rules, dispatches to the correct evaluator,
    and returns a full evaluation response.

    Examples:

        **Expense transaction**::

            {
              "subject_kind": "transaction",
              "event_type": "finance.expense.submitted",
              "actor": {"id": "E042", "type": "employee", "department": "sales"},
              "payload": {"amount": 150000, "currency": "JPY", "category": "entertainment"},
              "intent": "Submit entertainment expense for client dinner",
              "mode": "preflight"
            }

        **Contract document**::

            {
              "subject_kind": "document",
              "event_type": "legal.contract.draft_created",
              "actor": {"id": "E010", "type": "employee", "department": "legal"},
              "payload": {"clause_text": "...", "clause_type": "indemnity"},
              "intent": "Review indemnity clause in vendor agreement"
            }

        **Code diff (backward compatible)**::

            {
              "subject_kind": "code_diff",
              "event_type": "engineering.pr.opened",
              "actor": {"id": "agent:claude-code", "type": "agent", "department": "engineering"},
              "payload": {"diff": "--- a/main.py\\n+++ b/main.py\\n..."},
              "intent": "Add login endpoint"
            }
    """

    subject_kind: str = Field(
        ...,
        description=(
            "Subject kind determining evaluator dispatch. "
            "One of: code_diff, transaction, document, event, "
            "clause_set, creative, decision, identity."
        ),
        examples=["transaction", "document", "code_diff"],
    )
    event_type: str | None = Field(
        default=None,
        description=(
            "Dot-separated event name for scope resolution. "
            "When provided, the handler resolves applicable rule scopes "
            "from the event type mapping."
        ),
        examples=["finance.expense.submitted", "hr.overtime.filed", "engineering.pr.opened"],
    )
    actor: SubmissionActor
    payload: dict[str, Any] = Field(
        ...,
        description="Subject-specific data. Structure varies by subject_kind.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Freeform metadata (source system, timestamps, etc.).",
    )
    intent: str | None = Field(
        default=None,
        description="What the actor intends to do — used for intent-based rule selection.",
        examples=["Submit entertainment expense for client dinner"],
    )
    mode: Literal["preflight", "posthoc"] = Field(
        default="preflight",
        description="preflight = before action, posthoc = after action.",
    )
    scope: str | None = Field(
        default=None,
        description="Explicit scope override. If omitted, resolved from event_type + actor.",
    )
    max_rules: int = Field(default=20, ge=1, le=100)
    severity_min: str = Field(default="MEDIUM")
    correlation_id: str | None = Field(
        default=None,
        description="Business system's own ID for tracing.",
    )
    occurred_at: datetime | None = Field(
        default=None,
        description="When the event happened in the source system.",
    )


# ---------------------------------------------------------------------------
# Subject kind → surface mapping
# ---------------------------------------------------------------------------

_SUBJECT_KIND_TO_SURFACE: dict[str, str] = {
    "code_diff": "code",
    "document": "document",
    "transaction": "transaction",
    "event": "human_action",
    "clause_set": "contract",
    "creative": "message",
    "decision": "generic",
    "identity": "generic",
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("", response_model=EvaluateResponse)
async def submit(
    body: SubmissionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EvaluateResponse:
    """Submit any business event or artifact for rule evaluation.

    This is the **universal entry point** for all departments. It:

    1. Resolves rule scope from ``event_type`` and the actor's department.
    2. Maps ``subject_kind`` to the appropriate evaluation surface.
    3. Dispatches to the evaluation pipeline (same engine used by
       ``/evaluate`` and ``/events/ingest``).
    4. Returns a full evaluation response with per-rule verdicts,
       violations, remediations, and fix suggestions.

    **Scope resolution priority**:
    - Explicit ``scope`` field (if provided)
    - Mapped from ``event_type`` via the event scope resolver
    - Derived from actor's ``department``
    """
    # 1. Resolve scope
    resolved_scope = body.scope
    if not resolved_scope and body.event_type:
        resolver = EventScopeResolver()
        scopes = resolver.resolve(body.event_type)
        resolved_scope = scopes[0] if scopes else None
    if not resolved_scope and body.actor.department:
        resolved_scope = body.actor.department

    # 2. Resolve surface from subject kind
    surface = _SUBJECT_KIND_TO_SURFACE.get(body.subject_kind, "generic")

    # 3. Build evaluation service
    gemini = None
    try:
        from rulerepo_server.adapters.gemini.client import get_gemini_client

        gemini = get_gemini_client()
    except Exception:
        logger.warning("gemini_unavailable_for_submission")

    eval_svc = EvaluationService(session, gemini)

    # 4. Merge payload with context
    facts = {**body.payload}
    if body.metadata:
        facts["_metadata"] = body.metadata
    if body.correlation_id:
        facts["_correlation_id"] = body.correlation_id

    # 5. Dispatch to evaluation pipeline
    result = await eval_svc.evaluate(
        facts=facts,
        intent=body.intent,
        scope=resolved_scope,
        mode=body.mode,
        max_rules=body.max_rules,
        severity_min=body.severity_min,
        subject_kind=body.subject_kind,
        surface=surface,
        actor=body.actor.id,
        agent_id=body.actor.id if body.actor.type == "agent" else None,
        diff=body.payload.get("diff") if body.subject_kind == "code_diff" else None,
    )

    logger.info(
        "submission_evaluated",
        subject_kind=body.subject_kind,
        event_type=body.event_type,
        actor_id=body.actor.id,
        scope=resolved_scope,
        surface=surface,
        verdict=result.overall_verdict.value,
        rules_evaluated=result.rules_evaluated,
        violations=result.rules_violated,
        correlation_id=body.correlation_id,
    )

    return _result_to_response(result)
