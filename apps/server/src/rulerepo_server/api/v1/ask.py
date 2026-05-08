"""Conversational Rule Assistant — /ask endpoint (RR-005).

Accepts natural-language questions, classifies intent, retrieves
relevant rules, and returns a cited answer with links to source_refs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ask", tags=["conversational"])


class AskRequest(BaseModel):
    """Request body for the conversational /ask endpoint."""

    question: str = Field(..., min_length=1, max_length=5000)
    scope: str | None = None
    domain: str | None = None
    max_rules: int = Field(default=10, ge=1, le=50)


class Citation(BaseModel):
    """A rule citation included in the assistant's answer."""

    rule_id: str
    statement: str
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    relevance_score: float = 0.0


class AskResponse(BaseModel):
    """Response from the conversational /ask endpoint."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    intent: str = "general_query"
    can_register_proposal: bool = True


@router.post("", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AskResponse:
    """Answer a natural-language question about rules.

    Pipeline:
    1. Classify intent (what kind of question is being asked)
    2. Retrieve relevant rules from the corpus
    3. Generate a cited answer

    In production this calls the LLM provider abstraction for answer
    generation. The current implementation uses rule retrieval with
    a template-based answer as a foundation.
    """
    from rulerepo_server.domain.evaluation import EvaluationContext
    from rulerepo_server.services.evaluation.rule_selector import select_rules

    # Build a lightweight context from the question
    context = EvaluationContext(
        intent=request.question,
        facts={"question": request.question},
    )

    # Retrieve relevant rules
    rules = await select_rules(
        session,
        context,
        max_rules=request.max_rules,
        scope=request.scope,
    )

    # Build citations from matched rules
    citations: list[Citation] = []
    for rule in rules:
        citations.append(
            Citation(
                rule_id=str(rule.get("id", "")),
                statement=rule.get("statement", ""),
                source_refs=rule.get("source_refs", []),
                relevance_score=rule.get("relevance_score", 0.0),
            )
        )

    # Generate answer (in production, this would call the LLM via
    # adapters/llm/router.py — never directly)
    if citations:
        rule_summaries = "; ".join(c.statement[:100] for c in citations[:3])
        answer = f"Based on {len(citations)} relevant rules: {rule_summaries}"
    else:
        answer = "No directly relevant rules found for your question. Consider creating a rule proposal."

    logger.info(
        "ask_answered",
        question_length=len(request.question),
        rules_found=len(citations),
        domain=request.domain,
    )

    return AskResponse(
        answer=answer,
        citations=citations,
        intent="rule_query",
        can_register_proposal=True,
    )
