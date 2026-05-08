"""REST API routes for Event Evaluation (HR / Operations).

Provides a convenience endpoint for evaluating attendance, overtime,
leave, and other business events with sequence and calendar context.

See: CLAUDE.md §12.3, ADR 0005
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.evaluation import EvaluateResponse
from rulerepo_server.schemas.event import EventEvaluateRequest
from rulerepo_server.services.evaluation.service import EvaluationService

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluate/event", tags=["event-evaluation"])


def _get_evaluation_service(
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationService:
    gemini = None
    try:
        gemini = get_gemini_client()
    except Exception:
        logger.warning("gemini_unavailable_for_event_evaluation")
    return EvaluationService(session, gemini)


def _build_facts(request: EventEvaluateRequest) -> dict[str, Any]:
    """Build evaluation facts from the event request."""
    facts: dict[str, Any] = {
        "event_type": request.event_type,
        "evaluation_mode": request.evaluation_mode,
    }

    if request.employee_id:
        facts["employee_id"] = request.employee_id
    if request.date:
        facts["date"] = request.date
    if request.month:
        facts["month"] = request.month
    if request.hours is not None:
        facts["hours"] = request.hours
    if request.overtime_hours is not None:
        facts["overtime_hours"] = request.overtime_hours
    if request.leave_type:
        facts["leave_type"] = request.leave_type
    if request.leave_days is not None:
        facts["leave_days"] = request.leave_days
    if request.location:
        facts["location"] = request.location
        facts["jurisdiction"] = request.location

    # Include temporal context
    if request.event_window:
        facts["event_window"] = request.event_window.model_dump()
    if request.calendar_context:
        facts["calendar_context"] = request.calendar_context.model_dump()

    # Merge extra facts
    facts.update(request.extra_facts)

    return facts


@router.post("", response_model=EvaluateResponse)
async def evaluate_event(
    request: EventEvaluateRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> EvaluateResponse:
    """Evaluate an HR/operations event against applicable rules.

    Supports three modes:
    - single: evaluate the event alone
    - sequence: include monthly event window as context
    - calendar: include annual aggregates as context
    """
    facts = _build_facts(request)

    # Determine scope from event type
    scope = "hr/attendance"
    if "leave" in request.event_type:
        scope = "hr/leave"
    if request.location:
        scope = f"{scope}/{request.location.lower()}"

    result = await service.evaluate(
        facts=facts,
        scope=scope,
        mode=request.mode,
        max_rules=request.max_rules,
        severity_min=request.severity_min,
        subject_kind="event",
    )

    # Reuse the standard EvaluateResponse conversion
    from rulerepo_server.api.v1.evaluation import _result_to_response

    return _result_to_response(result)
