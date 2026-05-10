"""REST API router for the Conversational Rule Assistant.

See PROJECT.md §6.19 and CLAUDE.md §14.9.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AssistantTurnRequest(BaseModel):
    """Request body for POST /api/v1/assistant/turn."""

    session_id: str | None = None
    user_message: str = Field(..., min_length=1, max_length=5000)
    language: str = "ja"
    department_filter: list[str] = Field(default_factory=list)


class CitationResponse(BaseModel):
    """A rule citation in the assistant's response."""

    rule_id: str
    statement: str
    relevance_score: float = 0.0


class AssistantTurnResponse(BaseModel):
    """Response from the assistant turn endpoint."""

    session_id: str
    answer: str
    citations: list[CitationResponse] = Field(default_factory=list)
    intent: str = "general_query"
    follow_up_needed: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _require_assistant_enabled() -> None:
    """Raise 404 if assistant is disabled."""
    from rulerepo_server.core.feature_flags import get_feature_flags

    if not get_feature_flags().assistant_enabled:
        raise HTTPException(status_code=404, detail="Conversational Assistant is disabled")


@router.post("/turn", response_model=AssistantTurnResponse)
async def assistant_turn(
    body: AssistantTurnRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AssistantTurnResponse:
    """Process a single conversational turn.

    Accepts a user message, classifies intent, searches for relevant
    rules (filtered by department), and returns an answer with citations.
    """
    _require_assistant_enabled()

    from rulerepo_server.services.assistant.orchestrator import AssistantOrchestrator

    orchestrator = AssistantOrchestrator(session)
    result = await orchestrator.handle_turn(
        user_message=body.user_message,
        session_id=body.session_id,
        language=body.language,
        department_filter=body.department_filter or None,
    )

    return AssistantTurnResponse(
        session_id=result.session_id,
        answer=result.answer,
        citations=[
            CitationResponse(
                rule_id=c.rule_id,
                statement=c.statement,
                relevance_score=c.relevance_score,
            )
            for c in result.citations
        ],
        intent=result.intent,
        follow_up_needed=result.follow_up_needed,
    )
