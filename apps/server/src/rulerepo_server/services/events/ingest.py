"""Business event ingestion service — single endpoint for all business systems.

See PROJECT.md §6.11 and CLAUDE.md §14.8. Business systems push events;
the Rule Repository evaluates and returns verdicts synchronously.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.business_event import BusinessEvent
from rulerepo_server.domain.evaluation import EvaluationResult
from rulerepo_server.services.events.scope_resolver import EventScopeResolver

logger = get_logger(__name__)


class EventIngestionService:
    """Receives business events, resolves scope, dispatches to evaluation.

    This is the cross-organizational ingress point. The engineering-specific
    gateway endpoints remain for backward compatibility but this is the
    canonical endpoint for all departments.
    """

    def __init__(self, session: AsyncSession, gemini_client: Any | None = None) -> None:
        self._session = session
        self._gemini = gemini_client
        self._scope_resolver = EventScopeResolver()

    async def ingest(self, event: BusinessEvent) -> EvaluationResult:
        """Process a business event through the evaluation pipeline.

        Args:
            event: The business event to evaluate.

        Returns:
            EvaluationResult with verdicts and remediations.
        """
        logger.info(
            "event_ingested",
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            mode=event.mode,
            actor_id=event.actor.id,
            subject_kind=event.subject.kind.value,
        )

        # Resolve scopes from event type
        scopes = self._scope_resolver.resolve(event.event_type)

        # Merge resolved scopes into subject context
        subject = event.subject
        subject.context["resolved_scopes"] = scopes
        subject.context["event_type"] = event.event_type
        subject.context["correlation_id"] = event.correlation_id
        subject.context["mode"] = event.mode

        # Dispatch to the evaluation service
        from rulerepo_server.services.evaluation.service import EvaluationService

        # Map subject kind to a surface for prompt routing
        _kind_to_surface: dict[str, str] = {
            "transaction": "transaction",
            "document": "document",
            "message": "message",
            "event": "human_action",
        }
        surface = _kind_to_surface.get(subject.kind.value, "generic")

        eval_svc = EvaluationService(self._session, self._gemini)
        result = await eval_svc.evaluate(
            facts=subject.payload,
            scope=scopes[0] if scopes else None,
            mode=event.mode,
            surface=surface,
        )

        logger.info(
            "event_evaluated",
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            verdict=result.overall_verdict.value,
            rules_evaluated=result.rules_evaluated,
        )

        return result
